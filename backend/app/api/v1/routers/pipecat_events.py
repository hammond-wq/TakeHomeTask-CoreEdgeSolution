# app/api/v1/routers/pipecat_event.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict

from app.services.calllog_repo import CallLogRepo

router = APIRouter(prefix="/api/v1/pipecat", tags=["pipecat"])

class EventIn(BaseModel):
    provider_call_id: str
    event_type: str
    data: Dict[str, Any] = {}

@router.post("/event")
async def ing_event(evt: EventIn):
    """
    Record keyword hits, interruptions, or telemetry sent from the bot.
    """
    patch = {
        "last_event_type": evt.event_type,
        "last_event_data": evt.data,
       
        "analytics": evt.data
    }
    ok = await CallLogRepo.patch_by_provider(evt.provider_call_id, patch)
    if not ok:
        raise HTTPException(status_code=404, detail="provider_call_id not found")
    return {"ok": True}


