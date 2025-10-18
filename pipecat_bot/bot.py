import os
import time
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


from pipecat_whisker import WhiskerObserver


load_dotenv(override=True)

OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY  = os.getenv("DEEPGRAM_API_KEY")
CARTESIA_API_KEY  = os.getenv("CARTESIA_API_KEY")
CARTESIA_VOICE_ID = os.getenv("CARTESIA_VOICE_ID", "71a7ad14-091c-4e8e-a314-022ece01c121")
OPENAI_MODEL      = os.getenv("OPENAI_MODEL", "gpt-4.1")
BACKEND_BASE      = os.getenv("BACKEND_BASE", "http://localhost:8000") 

SYSTEM_PROMPT = "You are a friendly AI assistant. Keep replies short and conversational."


SEED_LOAD_NUMBER = os.getenv("SEED_LOAD_NUMBER")
SEED_DRIVER_NAME = os.getenv("SEED_DRIVER_NAME")
SEED_DRIVER_PHONE = os.getenv("SEED_DRIVER_PHONE")


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)

def _get_context_messages(context: LLMContext):
    """
    Return a list[{'role','content'}], compatible across Pipecat versions.
    """
    try:
        if hasattr(context, "to_universal_messages"):
            msgs = context.to_universal_messages()
            if isinstance(msgs, list):
                return msgs
        if hasattr(context, "messages"):
            msgs = context.messages
            if isinstance(msgs, list):
                return msgs
        if hasattr(context, "_messages"):
            return list(getattr(context, "_messages"))
    except Exception:
        pass
    return []

def _format_transcript(messages):
    """
    Turn LLMContext messages into a simple 'Agent/User' transcript.
    Filters out 'system' messages.
    """
    lines = []
    for m in messages or []:
        role = (m.get("role") or "").lower()
        if role == "system":
            continue
        content = (m.get("content") or "").strip()
        if not content:
            continue
        who = "Driver" if role == "user" else "Agent"
        lines.append(f"{who}: {content}")
    return "\n".join(lines)

async def _seed_calllog_if_needed(provider_call_id: str) -> None:
    """
    Ask backend to create a calllog row for this provider_call_id if it doesn't exist.
    Idempotent server-side.
    """
    payload = {
        "provider_call_id": provider_call_id,
        "load_number": SEED_LOAD_NUMBER,
        "driver_name": SEED_DRIVER_NAME,
        "driver_phone": SEED_DRIVER_PHONE,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as rc:
            r = await rc.post(f"{BACKEND_BASE}/api/v1/pipecat/seed", json=payload)
            if r.status_code >= 400:
                logger.error(f"Seed failed: {r.status_code} {r.text}")
            else:
                logger.info(f"Seed ok for provider_call_id={provider_call_id}")
    except Exception as e:
        logger.exception(f"Seed call failed: {e}")

async def _finalize(provider_call_id: str | None, transcript: str | None, started_at: dt.datetime | None):
    if not provider_call_id:
        logger.warning("No provider_call_id; skipping finalize POST.")
        return

    dur = 0.0
    if started_at:
        dur = max(0.0, (_utcnow() - started_at).total_seconds())

    payload = {
        "provider_call_id": provider_call_id,
        "transcript": (transcript or None),
        "extra": {"duration_secs": round(dur, 2)},
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as rc:
            r = await rc.post(f"{BACKEND_BASE}/api/v1/pipecat/finalize", json=payload)
            if r.status_code >= 400:
                logger.error(f"Finalize failed: {r.status_code} {r.text}")
            else:
                logger.info("✅ Finalized transcript to backend.")
    except Exception as e:
        logger.exception(f"Finalize call failed: {e}")

def _find_conv_in_obj(obj, depth=2):
    """
    Heuristically search attributes likely holding query/params dicts for 'conv'.
    Works with SmallWebRTCConnection internals and runner args.
    """
    if depth < 0 or obj is None:
        return None

    if isinstance(obj, dict):
        if "conv" in obj and isinstance(obj["conv"], (str, int)):
            return str(obj["conv"])
        # scan nested dicts
        for _, v in list(obj.items())[:20]:
            if isinstance(v, dict):
                hit = _find_conv_in_obj(v, depth - 1)
                if hit:
                    return hit
        return None

    try:
        for name in dir(obj):
            lname = name.lower()
            if ("query" in lname or "param" in lname or "args" in lname) and not lname.startswith("__"):
                try:
                    v = getattr(obj, name)
                except Exception:
                    continue
                if isinstance(v, dict):
                    hit = _find_conv_in_obj(v, depth - 1)
                    if hit:
                        return hit
    except Exception:
        pass
    return None

def _extract_conv_id(transport: BaseTransport, client, runner_args: RunnerArguments) -> str | None:
    
    hit = _find_conv_in_obj(client, depth=3)
    if hit:
        return hit
    
    for attr in ("connection", "_connection"):
        c = getattr(transport, attr, None)
        hit = _find_conv_in_obj(c, depth=3)
        if hit:
            return hit
    
    for attr in ("connection_query", "connection_params", "client_params"):
        qp = getattr(runner_args, attr, None)
        hit = _find_conv_in_obj(qp, depth=3)
        if hit:
            return hit
    
    return os.getenv("PIPECAT_CONV")



async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info("Starting bot: Deepgram STT + OpenAI LLM + Cartesia TTS")

    stt = DeepgramSTTService(api_key=DEEPGRAM_API_KEY)
    tts = CartesiaTTSService(api_key=CARTESIA_API_KEY, voice_id=CARTESIA_VOICE_ID)
    llm = OpenAILLMService(api_key=OPENAI_API_KEY, model=OPENAI_MODEL)

    
    context = LLMContext([{"role": "system", "content": SYSTEM_PROMPT}])
    agg = LLMContextAggregatorPair(context)

    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

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

    
    whisker = WhiskerObserver(pipeline)

    task = PipelineTask(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
        observers=[RTVIObserver(rtvi), whisker],
    )

    state = {"started_at": None, "provider_call_id": None}

    @transport.event_handler("on_client_connected")
    async def _on_client_connected(t, client):
        state["started_at"] = _utcnow()

        
        conv_from_client = _extract_conv_id(transport, client, runner_args)
        provider_call_id = conv_from_client or f"pipecat_{int(time.time() * 1000)}"
        if not conv_from_client:
            logger.warning(f"No ?conv= found in client; generated provider_call_id={provider_call_id}")

        state["provider_call_id"] = provider_call_id

        
        await _seed_calllog_if_needed(provider_call_id)

        logger.info(f"Client connected. provider_call_id={provider_call_id}")

        
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def _on_client_disconnected(t, client):
        logger.info("Client disconnected")
        try:
            msgs = _get_context_messages(context)
            transcript_text = _format_transcript(msgs)
            await _finalize(state["provider_call_id"], transcript_text, state["started_at"])
        finally:
            await task.cancel()

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
