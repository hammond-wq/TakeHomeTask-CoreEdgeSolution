# app/api/v1/routers/agent_webhook.py
from fastapi import APIRouter, Request, HTTPException
import hmac, hashlib, json, datetime as dt, re
from typing import Dict, Any
from app.core.config import settings
from app.services.supabase import SupabaseClient
from app.services.postprocess import summarize_transcript  

router = APIRouter(prefix="/api/v1/retell", tags=["retell"])


def _verify_signature(headers, body: bytes) -> bool:
    secret = (settings.retell_webhook_secret or "").encode()
    if not secret:  
        return True
    sig = headers.get("retell-signature") or headers.get("x-retell-signature")
    if not sig:
        return False
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def _classify_status(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["arrived","checked in","docked","at dock","in door"]): return "Arrived"
    if any(k in t for k in ["unloading","lumper","detention","in door"]):          return "Unloading"
    if any(k in t for k in ["delay","traffic","weather","stuck"]):                 return "Delayed"
    return "Driving"

def _detect_emergency(text: str) -> str | None:
    t = text.lower()
    if any(k in t for k in ["accident","crash","collision"]): return "Accident"
    if any(k in t for k in ["blowout","breakdown","flat","engine"]): return "Breakdown"
    if any(k in t for k in ["medical","injur","bleeding","faint"]):  return "Medical"
    return None

def _noisy(text: str) -> bool: return len(text.strip()) < 3 or "??" in text
def _short(text: str) -> bool: return text.strip().lower() in {"yes","no","ok","k","fine","later"}

def _handle_llm(payload: Dict[str, Any]) -> Dict[str, Any]:
    latest = (payload.get("latest_user") or "").strip()
    meta   = payload.get("metadata") or {}
    state  = meta.get("state") or {}

    # Emergency gate
    emerg = _detect_emergency(latest)
    if emerg:
        msg = (
            "I’m sorry to hear that. First — are you safe? Is anyone injured?\n"
            "Please share your exact location (highway and mile marker). Is the load secure?\n"
            "I’m connecting you to a human dispatcher now."
        )
        st = {**state, "scenario":"Emergency", "emergency_type":emerg}
        return {"text": msg, "end_call": False, "state": st}

    # Noisy
    if _noisy(latest):
        n = int(state.get("noisy_count", 0)) + 1
        if n >= 2:
            return {"text":"I’m still getting a lot of noise. I’ll escalate to a dispatcher now.", "end_call": True, "state":{**state,"noisy_count":n}}
        return {"text":"I’m getting a lot of noise—could you repeat that clearly once more?", "end_call": False, "state":{**state,"noisy_count":n}}

    # Uncooperative
    if _short(latest):
        s = int(state.get("short_count", 0)) + 1
        if s >= 3:
            return {"text":"I’ll let you go and follow up later. Drive safe.", "end_call": True, "state":{**state,"short_count":s}}
        return {"text":"Could you share your current location and ETA for this load?", "end_call": False, "state":{**state,"short_count":s}}

    # Open once
    if not state.get("opened"):
        driver = meta.get("driver_name","there")
        load   = meta.get("load_number","")
        open_line = f"Hi {driver}, this is Dispatch checking on load {load}. Could you give me a quick status update?"
        return {"text": open_line, "end_call": False, "state": {**state, "opened": True}}

    # Dispatch branching
    status = _classify_status(latest)
    st = {**state, "status": status, "scenario":"Dispatch"}

    if status in ("Driving","Delayed"):
        return {"text": "Thanks. What’s your current location and ETA? Any delays (traffic/weather/none)?", "end_call": False, "state": st}
    if status in ("Arrived","Unloading"):
        return {"text": "Got it. What’s your unloading status (door number / waiting for lumper)? And please remember to capture POD after unload.", "end_call": False, "state": st}

    return {"text":"Thanks. Anything else I should record for this load?", "end_call": False, "state": st}


async def _handle_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    transcript = payload.get("transcript_text") or payload.get("transcript") or ""
    retell_call_id = payload.get("call_id") or payload.get("id")
    meta = payload.get("metadata") or {}
    provider_call_id = meta.get("provider_call_id") or retell_call_id
    if not provider_call_id:
        raise HTTPException(400, "missing provider_call_id and call_id")

    summary = summarize_transcript(transcript)
    scenario = "Emergency" if summary.get("call_outcome") == "Emergency Escalation" else "Dispatch"

    patch = {
        "retell_call_id": retell_call_id,
        "status": "ended" if transcript else "updated",
        "call_end_time": dt.datetime.utcnow().isoformat() + "Z" if transcript else None,
        "transcript": transcript or None,
        "scenario": scenario,
        "structured_payload": summary,
    }
    patch = {k: v for k, v in patch.items() if v is not None}

    async with SupabaseClient().client() as c:
        params = {"provider_call_id": f"eq.{provider_call_id}"}
        r = await c.patch("/calllog", params=params, json=patch)
        if r.status_code >= 400:
            body = {"provider_call_id": provider_call_id, **patch}
            r = await c.post("/calllog", json=body)
            r.raise_for_status()

    return {"ok": True}

@router.post("/agent-webhook")
async def agent_webhook(request: Request):
    raw = await request.body()
    if not _verify_signature(request.headers, raw):
        raise HTTPException(status_code=401, detail="invalid signature")

    payload = json.loads(raw.decode("utf-8"))


    if "latest_user" in payload or ("history" in payload and isinstance(payload["history"], list)):
        return _handle_llm(payload)
    else:
        return await _handle_event(payload)
