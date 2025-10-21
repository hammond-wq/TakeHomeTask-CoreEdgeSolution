# pipecat_bot/bot.py
import os
import re
import math
import datetime as dt
import httpx
from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams

try:
    from pipecat_whisker import WhiskerObserver
except Exception:
    WhiskerObserver = None


# ENV & CONFIG
load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY")
CARTESIA_VOICE_ID = os.getenv("CARTESIA_VOICE_ID", "71a7ad14-091c-4e8e-a314-022ece01c121")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
BACKEND_BASE = os.getenv("BACKEND_BASE", "http://127.0.0.1:8000")
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "You are a friendly Dispatch call agent. Keep replies short, confirm load + driver, collect status (ETA/location/delay reason), and escalate emergencies."
)

KW_DEFAULT = ["emergency", "breakdown", "accident", "police", "hospital"]
KEYWORDS = [k.strip().lower() for k in os.getenv("PIPECAT_KEYWORDS", ",".join(KW_DEFAULT)).split(",") if k.strip()]



# Utility Helpers
def _utcnow():
    return dt.datetime.now(dt.timezone.utc)


def _format_transcript(messages):
    lines = []
    for m in messages or []:
        role = (m.get("role") or "").lower()
        content = (m.get("content") or "").strip()
        if not content:
            continue
        who = "Driver" if role == "user" else "Agent"
        lines.append(f"{who}: {content}")
    return "\n".join(lines)


def _analytics_from_transcript(transcript: str) -> dict:
    low = (transcript or "").lower()
    kw_hits = {kw: len(re.findall(rf"\\b{re.escape(kw)}\\b", low)) for kw in KEYWORDS}
    lines = [ln.strip() for ln in (transcript or "").splitlines() if ln.strip()]
    driver_turns = agent_turns = interruptions_est = 0
    prev = None
    for ln in lines:
        if ln.startswith("Driver:"):
            driver_turns += 1
            if prev == "Agent":
                interruptions_est += 1
            prev = "Driver"
        elif ln.startswith("Agent:"):
            agent_turns += 1
            prev = "Agent"

    return {
        "keyword_hits": kw_hits,
        "driver_turns": driver_turns,
        "agent_turns": agent_turns,
        "interruptions_est": interruptions_est,
        "tokens_estimated": int(len(transcript) / 4) if transcript else 0,
    }


async def _post_rtvi_event(call_id, event, data):
    """Send real-time RTVI events to backend analytics."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as rc:
            await rc.post(f"{BACKEND_BASE}/api/v1/pipecat/rtvi", json={
                "provider_call_id": call_id,
                "event": event,
                **data
            })
        logger.info(f"RTVI event sent: {event}")
    except Exception as e:
        logger.warning(f"RTVI event post failed: {e}")


async def _finalize(provider_call_id: str | None, transcript: str | None, started_at: dt.datetime | None):
    """Finalize transcript and send analytics summary."""
    if not provider_call_id:
        logger.warning("No provider_call_id; skipping finalize POST.")
        return

    duration = 0.0
    if started_at:
        duration = max(0.0, (_utcnow() - started_at).total_seconds())

    analytics = _analytics_from_transcript(transcript or "")
    analytics["duration_secs"] = round(duration, 2)

    payload = {
        "provider_call_id": provider_call_id,
        "transcript": transcript,
        "extra": analytics,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as rc:
            r = await rc.post(f"{BACKEND_BASE}/api/v1/pipecat/finalize", json=payload)
            if r.status_code < 400:
                logger.info("Finalized transcript + analytics to backend.")
            else:
                logger.error(f"Finalize failed: {r.status_code} {r.text}")
    except Exception as e:
        logger.exception(f"Finalize call failed: {e}")


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info("Starting bot with Deepgram STT + OpenAI LLM + Cartesia TTS")

    stt = DeepgramSTTService(api_key=DEEPGRAM_API_KEY)
    tts = CartesiaTTSService(api_key=CARTESIA_API_KEY, voice_id=CARTESIA_VOICE_ID)
    llm = OpenAILLMService(api_key=OPENAI_API_KEY, model=OPENAI_MODEL)

    base_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    context = LLMContext(base_messages)
    agg = LLMContextAggregatorPair(context)

    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))
    observers = [RTVIObserver(rtvi)]
    if WhiskerObserver:
        observers.append(WhiskerObserver(rtvi))

    pipeline = Pipeline([
        transport.input(),
        rtvi,
        stt,
        agg.user(),
        llm,
        tts,
        transport.output(),
        agg.assistant(),
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
        observers=observers,
    )

    state = {"started_at": None, "provider_call_id": None}

    @transport.event_handler("on_client_connected")
    async def _on_client_connected(t, client):
        from random import randint
        state["started_at"] = _utcnow()
        state["provider_call_id"] = f"pipecat_{randint(1000000, 9999999)}"
        logger.info(f"Client connected. provider_call_id={state['provider_call_id']}")
        await _post_rtvi_event(state["provider_call_id"], "call_started", {"time": str(_utcnow())})
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def _on_client_disconnected(t, client):
        logger.info("Client disconnected")
        try:
            messages = context.to_universal_messages() if hasattr(context, "to_universal_messages") else []
            transcript_text = _format_transcript(messages)
            await _post_rtvi_event(state["provider_call_id"], "transcript_final", {"transcript": transcript_text})
            await _finalize(state["provider_call_id"], transcript_text, state["started_at"])
        finally:
            await task.cancel()

    # -------------------------------------------------------------------------
    # RTVI live event hooks
    # -------------------------------------------------------------------------
    @rtvi.event_handler("interrupt_detected")
    async def _on_interrupt(event):
        await _post_rtvi_event(state["provider_call_id"], "interrupt_detected", {"at": str(_utcnow())})

    @rtvi.event_handler("sentiment_update")
    async def _on_sentiment(event):
        await _post_rtvi_event(state["provider_call_id"], "sentiment_update", {"sentiment": event.get("sentiment")})

    @rtvi.event_handler("keyword_detected")
    async def _on_keyword(event):
        kw = event.get("keyword")
        await _post_rtvi_event(state["provider_call_id"], "keyword_detected", {"keyword": kw})

    @rtvi.event_handler("metrics_final")
    async def _on_metrics(event):
        await _post_rtvi_event(state["provider_call_id"], "metrics_final", {
            "metrics": {
                "duration_secs": event.get("duration_secs"),
                "tokens_used": event.get("tokens_used"),
                "sentiment_final": event.get("sentiment", "neutral")
            }
        })

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    transport_params = {
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            turn_analyzer=LocalSmartTurnAnalyzerV3(),
        ),
    }
    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main
    logger.info("Loading models…")
    main()
