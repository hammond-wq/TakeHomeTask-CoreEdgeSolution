from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
import hmac, hashlib, json, datetime as dt
from typing import Any, Dict, List

from app.core.config import settings
from app.services.supabase import SupabaseClient
from app.services.postprocess import summarize_transcript
from app.services.agents_repo import AgentsRepo
from app.services.drivers_repo import DriversRepo

router = APIRouter(prefix="/api/v1/retell", tags=["retell"])



def _verify_signature(headers, body: bytes) -> bool:
    secret = (settings.retell_webhook_secret or "").encode()
    if not secret:
        return True
    sig = headers.get("x-retell-signature") or headers.get("retell-signature")
    if not sig:
        return False
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)



async def _patch_calllog(where: dict, patch: dict) -> bool:
    async with SupabaseClient().client() as c:
        params = {}
        if where.get("provider_call_id"):
            params["provider_call_id"] = f"eq.{where['provider_call_id']}"
        if where.get("retell_call_id"):
            params["retell_call_id"] = f"eq.{where['retell_call_id']}"
        if not params:
            return False
        r = await c.patch("/calllog", params=params, json=patch)
        try:
            data = r.json()
        except Exception:
            data = r.text
        print("↪️  PATCH /calllog", r.status_code, data)
        return r.status_code < 400

async def _post_calllog(row: dict):
    async with SupabaseClient().client() as c:
        r = await c.post("/calllog", json=row)
        try:
            data = r.json()
        except Exception:
            data = r.text
        print("↪️  POST /calllog", r.status_code, data)
        return r



def _pluck_call(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retell webhook shape is usually:
      { "event": "call_ended", "call": { ... } }
    Some older docs show "data" instead of "call". Handle both.
    """
    return (payload.get("call") or payload.get("data") or {}) if isinstance(payload, dict) else {}

def _text_from_transcript_object(obj: Any) -> str:
    """
    transcript_object is an array like:
      [{ role: "user"/"assistant", content: "..." }, ...]
    Join as lines.
    """
    if not isinstance(obj, list):
        return ""
    lines: List[str] = []
    for u in obj:
        if not isinstance(u, dict):
            continue
        role = (u.get("role") or "").strip().lower()
        content = (u.get("content") or "").strip()
        if not content:
            continue
        who = "Driver" if role == "user" else "Agent"
        lines.append(f"{who}: {content}")
    return "\n".join(lines)

def _pluck_transcript(call_obj: Dict[str, Any]) -> str:
    """
    Prefer 'transcript' (string), then 'transcript_text', then 'transcript_object'.
    """
    if not isinstance(call_obj, dict):
        return ""
    t = call_obj.get("transcript") or call_obj.get("transcript_text")
    if isinstance(t, str) and t.strip():
        return t.strip()
    
    obj = call_obj.get("transcript_object") or call_obj.get("transcript_with_tool_calls")
    s = _text_from_transcript_object(obj)
    return s.strip()


@router.post("/webhook")
async def retell_webhook(request: Request):
    raw = await request.body()
    if not _verify_signature(request.headers, raw):
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
      
        return {"ok": True}


    if isinstance(payload, dict) and "challenge" in payload:
        return {"challenge": payload["challenge"]}

    event = (payload.get("event") or "").lower()
    call = _pluck_call(payload)

    
    retell_call_id = call.get("call_id") or call.get("id")
    metadata = call.get("metadata") or {}
    provider_call_id = metadata.get("provider_call_id")
    load_number = metadata.get("load_number")

    dyn = call.get("retell_llm_dynamic_variables") or {}
    driver_name = dyn.get("driver_name") or metadata.get("driver_name")
    driver_phone = dyn.get("driver_phone") or metadata.get("driver_phone")

    
    if event == "call_started":
        patch = {
            "retell_call_id": retell_call_id,
            "load_number": load_number,
            "status": "started",
        }
     
        patched = False
        if provider_call_id:
            patched = await _patch_calllog({"provider_call_id": provider_call_id}, patch)
        if not patched and retell_call_id:
            patched = await _patch_calllog({"retell_call_id": retell_call_id}, patch)
        
        return {"ok": True, "patched": patched}

   
    if event in {"call_ended", "call_analyzed"}:
        transcript = _pluck_transcript(call)
        summary = summarize_transcript(transcript or "")
        scenario = "Emergency" if summary.get("call_outcome") == "Emergency Escalation" else "Dispatch"

      
        agent_db_id = (await AgentsRepo.ensure_agent_id()) or 1
        driver_db_id = (await DriversRepo.ensure_driver_id(driver_name, driver_phone)) or 1

        patch = {
            "retell_call_id": retell_call_id,
            "load_number": load_number,
            "structured_payload": summary,
            "transcript": transcript or None,
            "scenario": scenario,
            "status": "ended",
            "call_end_time": dt.datetime.utcnow().isoformat() + "Z",
            "agent_id": agent_db_id,
            "driver_id": driver_db_id,
        }
       
        patch = {k: v for k, v in patch.items() if v is not None}

        updated = False
        if provider_call_id:
            updated = await _patch_calllog({"provider_call_id": provider_call_id}, patch)
        if not updated and retell_call_id:
            updated = await _patch_calllog({"retell_call_id": retell_call_id}, patch)

        if not updated:
            base = {
                "provider_call_id": provider_call_id,
                "retell_call_id": retell_call_id,
                **patch,
            }
            await _post_calllog(base)

        return {"ok": True, "finalized": True}

    # Unknown or unsupported event → ack
    print("ℹ️ Unknown/ignored webhook event:", event)
    return {"ok": True}
