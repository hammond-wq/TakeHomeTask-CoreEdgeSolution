# app/api/v1/routers/pipecat_events.py
from __future__ import annotations
import asyncio
import datetime as dt
import json
from fastapi import APIRouter, Request, BackgroundTasks
from app.services.supabase import SupabaseClient
from app.services.calllog_repo import CallLogRepo
from app.services.postprocess import summarize_transcript
import structlog

router = APIRouter(prefix="/api/v1/pipecat", tags=["pipecat-events"])

logger = structlog.get_logger("pipecat-events")

# RTVI (Real-Time Voice Interaction) 

async def handle_rtvi_event(payload: dict):
    """Handles incoming RTVI event payloads and stores analytics in Supabase."""
    event_type = payload.get("event")
    call_id = payload.get("provider_call_id") or payload.get("session_id") or "unknown"
    now_iso = dt.datetime.utcnow().isoformat() + "Z"


    analytics_data = {
        "provider_call_id": call_id,
        "event_type": event_type,
        "timestamp": now_iso,
    }

    try:
        if event_type == "metrics_final":
          
            metrics = payload.get("metrics", {})
            duration = metrics.get("duration_secs")
            tokens = metrics.get("tokens_used")

            analytics_data.update({
                "duration_secs": duration,
                "tokens_used": tokens,
                "sentiment": metrics.get("sentiment_final", "neutral")
            })

            
            patch = {"extra": analytics_data}
            await CallLogRepo.patch_by_provider(call_id, patch)
            logger.info("RTVI metrics_final logged", call_id=call_id)

        elif event_type == "interrupt_detected":
            await _increment_counter(call_id, "interruptions")
            logger.info("RTVI interruption detected", call_id=call_id)

        elif event_type == "keyword_detected":
            keyword = payload.get("keyword")
            await _log_keyword(call_id, keyword)
            logger.info("RTVI keyword logged", call_id=call_id, keyword=keyword)

        elif event_type == "sentiment_update":
            sentiment = payload.get("sentiment")
            patch = {"extra->>sentiment": sentiment}
            await CallLogRepo.patch_by_provider(call_id, patch)
            logger.info("RTVI sentiment updated", call_id=call_id, sentiment=sentiment)

        elif event_type == "transcript_final":
            transcript = payload.get("transcript") or ""
            summary = summarize_transcript(transcript)
            patch = {
                "structured_payload": summary,
                "transcript": transcript,
                "status": "ended",
                "scenario": "Emergency" if summary.get("call_outcome") == "Emergency Escalation" else "Dispatch"
            }
            await CallLogRepo.patch_by_provider(call_id, patch)
            logger.info("RTVI transcript finalized", call_id=call_id)

        else:
            logger.debug("RTVI unknown event ignored", event=event_type)

    except Exception as e:
        logger.error("RTVI event handling failed", error=str(e), payload=payload)


# Helper async functions


async def _increment_counter(call_id: str, field: str):
    """Increment a numeric counter in Supabase for a given call_id."""
    try:
        async with SupabaseClient().client() as c:
            query = f"update calllog set extra = jsonb_set(coalesce(extra, '{{}}'::jsonb), '{{{field}}}', ((coalesce(extra->>'{field}', '0')::int + 1)::text)::jsonb, true) where provider_call_id = '{call_id}';"
            await c.rpc("exec_sql", {"sql": query})
    except Exception as e:
        logger.warning("Failed to increment counter", error=str(e))

async def _log_keyword(call_id: str, keyword: str):
    """Append a keyword occurrence to calllog.extra.keywords"""
    try:
        async with SupabaseClient().client() as c:
            query = f"update calllog set extra = jsonb_set(coalesce(extra, '{{}}'::jsonb), '{{keywords}}', coalesce(extra->'keywords', '[]'::jsonb) || to_jsonb('{keyword}'), true) where provider_call_id = '{call_id}';"
            await c.rpc("exec_sql", {"sql": query})
    except Exception as e:
        logger.warning("Failed to log keyword", error=str(e))


#  POST Endpoint for Internal RTVI  Events


@router.post("/rtvi")
async def pipecat_rtvi_ingest(request: Request, background_tasks: BackgroundTasks):
    """
    Ingests RTVI (Real-Time Voice Interaction) events streamed from Pipecat.
    Does NOT expose new behavior externally — same /pipecat prefix used.
    """
    payload = await request.json()
    background_tasks.add_task(handle_rtvi_event, payload)
    return {"ok": True, "received": payload.get("event")}
