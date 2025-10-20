# app/api/v1/routers/pipecat_adapter.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Optional
import datetime as dt

from app.services.supabase import SupabaseClient
from app.services.postprocess import summarize_transcript
from app.services.agents_repo import AgentsRepo
from app.services.drivers_repo import DriversRepo
from app.services.calllog_repo import CallLogRepo

router = APIRouter(prefix="/api/v1/pipecat", tags=["pipecat"])

class StartOut(BaseModel):
    endpoint: str  # RTVI/SmallWebRTC start URL

@router.post("/start", response_model=StartOut)
async def start_pipecat():
    import os
    endpoint = os.getenv("PIPECAT_ENDPOINT", "http://127.0.0.1:7860/start")
    return StartOut(endpoint=endpoint)

# ---- Seed ----
class SeedIn(BaseModel):
    provider_call_id: str
    load_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None

@router.post("/seed")
async def seed_call(body: SeedIn):
    agent_id = await AgentsRepo.ensure_agent_id()
    driver_id = await DriversRepo.ensure_driver_id(body.driver_name, body.driver_phone)
    row = {
        "provider_call_id": body.provider_call_id,
        "load_number": body.load_number,
        "status": "initiated",
        "structured_payload": {},
        "scenario": "Dispatch",
        "agent_id": agent_id,
        "driver_id": driver_id,
    }
    try:
        await CallLogRepo.post(row)
        return {"ok": True}
    except Exception as e:
        # If row already exists (unique constraint), treat as ok
        # or raise if you prefer strict.
        return {"ok": True, "note": f"seed post skipped/failed: {e}"}

# ---- Finalize (robust) ----
class FinalizeIn(BaseModel):
    provider_call_id: Optional[str] = Field(default=None)
    transcript: Optional[str] = Field(default=None)
    extra: dict[str, Any] = Field(default_factory=dict)

async def _find_recent_initiated_pipecat():
    since = (dt.datetime.utcnow() - dt.timedelta(minutes=30)).isoformat() + "Z"
    async with SupabaseClient().client() as c:
        r = await c.get(
            "/calllog",
            params={
                "select": "id,provider_call_id,created_at,status",
                "status": "eq.initiated",
                "provider_call_id": "like.pipecat_%",
                "created_at": f"gte.{since}",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
        if r.status_code >= 400:
            return None
        rows = r.json() or []
        return rows[0] if rows else None

@router.post("/finalize")
async def finalize_call(body: FinalizeIn):
    pid = (body.provider_call_id or "").strip()

    # Build the patch from transcript
    transcript = (body.transcript or "").strip()
    summary = summarize_transcript(transcript)

    patch = {
        "structured_payload": summary,
        "transcript": transcript or None,
        "status": "ended",
        "scenario": "Dispatch" if summary.get("call_outcome") != "Emergency Escalation" else "Emergency",
        "call_end_time": dt.datetime.utcnow().isoformat() + "Z",
        "call_outcome": summary.get("call_outcome"),
        "conflicts": {},
    }
    if body.extra:
        patch["extra"] = body.extra  # requires 'extra' JSONB column in calllog

    # 1) Try direct patch by provider_call_id
    if pid:
        ok = await CallLogRepo.patch_by_provider(pid, patch)
        if ok:
            return {"ok": True, "provider_call_id": pid}

        # 2) Fallback: pick most recent initiated pipecat row
        latest = await _find_recent_initiated_pipecat()
        if latest and latest.get("provider_call_id"):
            pid2 = latest["provider_call_id"]
            ok2 = await CallLogRepo.patch_by_provider(pid2, patch)
            if ok2:
                return {"ok": True, "provider_call_id": pid2}

        # 3) Last resort: create a row so data isn't lost
        try:
            await CallLogRepo.post({
                "provider_call_id": pid,
                "status": "ended",
                "structured_payload": summary,
                "transcript": transcript or None,
                "scenario": patch["scenario"],
                "call_end_time": patch["call_end_time"],
                "call_outcome": patch["call_outcome"],
                "conflicts": {},
                "extra": body.extra or {},
            })
            return {"ok": True, "provider_call_id": pid, "created": True}
        except Exception as e:
            raise HTTPException(404, f"no calllog row for provider_call_id={pid} ({e})")

    # no pid provided → use most recent 'initiated' pipecat row
    latest = await _find_recent_initiated_pipecat()
    if latest and latest.get("provider_call_id"):
        pid = latest["provider_call_id"]
        ok = await CallLogRepo.patch_by_provider(pid, patch)
        if ok:
            return {"ok": True, "provider_call_id": pid}
    return {"ok": False, "reason": "no_target_row"}
