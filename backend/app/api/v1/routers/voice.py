from __future__ import annotations

import datetime as dt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.calllog_repo import CallLogRepo
from app.services.postprocess import summarize_transcript

router = APIRouter(prefix="/api/v1/pipecat", tags=["pipecat"])

class FinalizeIn(BaseModel):
    provider_call_id: str
    transcript: str | None = None
    extra: dict | None = None

@router.post("/finalize")
async def finalize_pipecat(body: FinalizeIn):
    if not (body.provider_call_id and body.provider_call_id.strip()):
        raise HTTPException(400, "provider_call_id is required")

    summary = summarize_transcript(body.transcript or "")
  
    if body.extra:
        summary = {**summary, "pipecat_metrics": body.extra}

    patch = {
        "structured_payload": summary,
        "transcript": (body.transcript or "").strip() or None,
        "scenario": "Emergency" if summary.get("call_outcome") == "Emergency Escalation" else "Dispatch",
        "status": "ended",
        "call_end_time": dt.datetime.utcnow().isoformat() + "Z",
    }

    ok = await CallLogRepo.patch_by_provider(body.provider_call_id, patch)
    if not ok:
   
        raise HTTPException(404, "calllog row not found for that provider_call_id")

    return {"ok": True}
