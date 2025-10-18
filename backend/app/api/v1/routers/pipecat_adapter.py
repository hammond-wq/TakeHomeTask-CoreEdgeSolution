from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.supabase import SupabaseClient
from app.services.postprocess import summarize_transcript
from app.services.agents_repo import AgentsRepo
from app.services.drivers_repo import DriversRepo
from app.services.calllog_repo import CallLogRepo

router = APIRouter(prefix="/api/v1/pipecat", tags=["pipecat"])



async def _get_calllog_by_provider(pid: str) -> Optional[Dict[str, Any]]:
    async with SupabaseClient().client() as c:
        r = await c.get("/calllog", params={"provider_call_id": f"eq.{pid}", "limit": "1"})
        if r.status_code >= 400:
            return None
        rows = r.json() or []
        return rows[0] if rows else None

def _now_iso() -> str:
    return dt.datetime.utcnow().isoformat() + "Z"



class StartOut(BaseModel):
    endpoint: str 

@router.post("/start", response_model=StartOut)
async def start_pipecat():
    import os
    endpoint = os.getenv("PIPECAT_ENDPOINT", "http://127.0.0.1:7860/start")
    return StartOut(endpoint=endpoint)



class SeedIn(BaseModel):
    provider_call_id: str
    load_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None

@router.post("/seed")
async def seed_call(body: SeedIn):
    """Create calllog row up-front so /finalize can patch reliably (idempotent)."""
    existing = await _get_calllog_by_provider(body.provider_call_id)
    if existing:
        return {"ok": True, "already": True}

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
        "extra": {},  
    }
    try:
        await CallLogRepo.post(row)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, f"seed failed: {e}")



class FinalizeIn(BaseModel):
    provider_call_id: Optional[str] = Field(default=None)
    transcript: Optional[str] = Field(default=None)
    extra: Dict[str, Any] = Field(default_factory=dict)

async def _find_recent_initiated_pipecat() -> Optional[Dict[str, Any]]:
    """Find the latest 'initiated' pipecat row within the last 30 minutes."""
    since = (dt.datetime.utcnow() - dt.timedelta(minutes=30)).isoformat() + "Z"
    async with SupabaseClient().client() as c:
        r = await c.get(
            "/calllog",
            params={
                "select": "id,provider_call_id,created_at,status,extra",
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
    """
    Called by the Pipecat bot when the session ends.
    - Summarizes transcript into structured_payload.
    - Merges any analytics in `body.extra` with the row's existing `extra`.
    - Marks status=ended and stamps call_end_time.
    """
    pid = (body.provider_call_id or "").strip()

    # Locate target row
    row: Optional[Dict[str, Any]] = None
    if pid:
        row = await _get_calllog_by_provider(pid)
    else:
        row = await _find_recent_initiated_pipecat()
        pid = row.get("provider_call_id") if row else None

    if not pid or not row:
        raise HTTPException(404, "no calllog row for provider_call_id")

    
    transcript = (body.transcript or "").strip()
    summary = summarize_transcript(transcript)

   
    existing_extra = dict(row.get("extra") or {})
    incoming_extra = dict(body.extra or {})
    merged_extra = {**existing_extra, **incoming_extra}

    patch = {
        "structured_payload": summary,
        "transcript": transcript or None,
        "status": "ended",
        "scenario": "Dispatch" if summary.get("call_outcome") != "Emergency Escalation" else "Emergency",
        "call_end_time": _now_iso(),
        "call_outcome": summary.get("call_outcome"),
        "conflicts": {},
        "extra": merged_extra,
    }

    ok = await CallLogRepo.patch_by_provider(pid, patch)
    if not ok:
        raise HTTPException(404, f"no calllog row for provider_call_id={pid}")
    return {"ok": True, "provider_call_id": pid}
