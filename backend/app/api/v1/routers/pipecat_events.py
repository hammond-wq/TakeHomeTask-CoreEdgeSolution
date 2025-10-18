from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.calllog_repo import CallLogRepo
from app.services.supabase import SupabaseClient

router = APIRouter(prefix="/api/v1/pipecat", tags=["pipecat"])

async def _get_calllog_by_provider(pid: str) -> Optional[Dict[str, Any]]:
    async with SupabaseClient().client() as c:
        r = await c.get("/calllog", params={"provider_call_id": f"eq.{pid}", "limit": "1"})
        if r.status_code >= 400:
            return None
        rows = r.json() or []
        return rows[0] if rows else None

class EventIn(BaseModel):
    provider_call_id: str
    event_type: str
    data: Dict[str, Any] = {}

@router.post("/event")
async def ing_event(evt: EventIn):
    """
    Merge low-volume analytics into calllog.extra.
    Structure of `extra` (example):
      {
        "interruptions": 2,
        "keyword_counts": {"delay": 3, "weather": 1},
        "sentiments": [{"at": "...", "value": "positive"}, ...],
        "estimated_tokens_total": 1234,
        "events_log": [{"type": "...", ...}, ...]
      }
    """
    row = await _get_calllog_by_provider(evt.provider_call_id)
    if not row:
        raise HTTPException(status_code=404, detail="provider_call_id not found")

    extra = dict(row.get("extra") or {})

    
    events_log = list(extra.get("events_log") or [])
    if len(events_log) > 200:
        events_log = events_log[-200:]

    etype = evt.event_type

    if etype == "interruption":
        extra["interruptions"] = int(extra.get("interruptions") or 0) + 1

    elif etype == "keyword":
        kw = (evt.data.get("keyword") or "").strip().lower()
        if kw:
            kc = dict(extra.get("keyword_counts") or {})
            kc[kw] = int(kc.get(kw) or 0) + 1
            extra["keyword_counts"] = kc

    elif etype == "sentiment":
        sentiments = list(extra.get("sentiments") or [])
        sentiments.append({"at": evt.data.get("at"), "value": evt.data.get("value")})
        if len(sentiments) > 300:
            sentiments = sentiments[-300:]
        extra["sentiments"] = sentiments

    elif etype == "tokens_estimated":
        t = int(evt.data.get("estimated_tokens") or 0)
        extra["estimated_tokens_total"] = int(extra.get("estimated_tokens_total") or 0) + max(0, t)

    
    entry = {"type": etype, **evt.data}
    events_log.append(entry)
    extra["events_log"] = events_log

   
    patch = {
        "last_event_type": etype,
        "last_event_data": evt.data,
        "extra": extra,
    }
    ok = await CallLogRepo.patch_by_provider(evt.provider_call_id, patch)
    if not ok:
        raise HTTPException(status_code=404, detail="provider_call_id not found on patch")
    return {"ok": True}
