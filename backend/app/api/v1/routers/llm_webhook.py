from __future__ import annotations

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
import json
import re
from typing import Tuple, List
from app.services.supabase import SupabaseClient
from app.services.postprocess import summarize_transcript

router = APIRouter(prefix="/api/v1/retell", tags=["retell"])



async def _patch_calllog_by_retell(retell_call_id: str, patch: dict) -> None:
    if not retell_call_id:
        return
    async with SupabaseClient().client() as c:
        await c.patch("/calllog", params={"retell_call_id": f"eq.{retell_call_id}"}, json=patch)



TIME_RE = re.compile(r"\b(?:at\s*)?(\d{1,2}:\d{2}\s*(?:am|pm)?)\b|\b(?:in\s*)?(\d+)\s*(?:min|mins|minutes|hr|hrs|hours)\b", re.I)
CITY_HWY_RE = re.compile(r"\b(?:i-\d{1,3}|us-\d{1,3}|hwy\s*\d+|highway\s*\d+|[A-Z][a-z]+(?:,\s*[A-Z]{2})?)\b")
REASON_RE = re.compile(r"\b(traffic|weather|accident|construction|breakdown|tire|blowout|police|road\s*closure|detour)\b", re.I)
UNLOAD_RE = re.compile(r"\b(door\s*\d+|in\s*door|waiting\s*for\s*lumper|lumper|detention|unloading|checked\s*in)\b", re.I)

def extract_eta(text: str) -> str | None:
    m = TIME_RE.search(text or "")
    return m.group(0) if m else None

def extract_location(text: str) -> str | None:
    m = CITY_HWY_RE.search(text or "")
    return m.group(0) if m else None

def extract_delay_reason(text: str) -> str | None:
    m = REASON_RE.search(text or "")
    return m.group(1).title() if m else None

def extract_unloading(text: str) -> str | None:
    m = UNLOAD_RE.search(text or "")
    if not m: return None
    val = m.group(0).strip().title()
    return "In Door" if val.lower().startswith("in door") else val

def _classify_status(text: str) -> str:
    t = (text or "").lower()
    if any(k in t for k in ["arrived","checked in","docked","at dock","in door"]): return "Arrived"
    if any(k in t for k in ["unloading","lumper","detention","in door"]):          return "Unloading"
    if any(k in t for k in ["delay","late","behind","traffic","weather","stuck"]): return "Delayed"
    return "Driving"

def _detect_emergency(text: str) -> str | None:
    t = (text or "").lower()
    if any(k in t for k in ["accident","crash","collision"]): return "Accident"
    if any(k in t for k in ["blowout","breakdown","flat","engine"]): return "Breakdown"
    if any(k in t for k in ["medical","injur","bleeding","faint"]): return "Medical"
    return None

def _is_noisy(text: str) -> bool:
    return len((text or "").strip()) < 3 or "??" in (text or "")

def _is_uncoop(text: str) -> bool:
    return (text or "").strip().lower() in {"yes","no","ok","k","fine","later"}

def _latest_user(transcript: list) -> str:
    if not isinstance(transcript, list): return ""
    for utt in reversed(transcript):
        if isinstance(utt, dict) and utt.get("role") == "user":
            return (utt.get("content") or "").strip()
    return ""

def _confirm_wrap(state: dict) -> Tuple[str, bool, dict]:
    status = state.get("driver_status") or "Driving"
    loc = state.get("current_location") or "N/A"
    eta = state.get("eta") or "N/A"
    reason = state.get("delay_reason") or "None"
    unload = state.get("unloading_status") or "N/A"

    
    if status in ("Arrived","Unloading"):
        outcome = "Arrival Confirmation"
    else:
        outcome = "In-Transit Update"
    state["call_outcome"] = outcome

    msg = f"Thanks. Logging your status: {status}. Location: {loc}. ETA: {eta}. Delay reason: {reason}. Unloading: {unload}. I’ll update dispatch now."
    return msg, True, state

def draft_reply(latest_user: str, state: dict) -> tuple[str, bool, dict]:
    
    emerg = _detect_emergency(latest_user)
    if emerg:
        state.update({"scenario":"Emergency","emergency_type":emerg})
        return (
            "I’m sorry to hear that. Are you safe? Any injuries? Please share exact location and whether the load is secure. I’m connecting you to a dispatcher now.",
            False,
            state
        )

    
    if _is_noisy(latest_user):
        n = int(state.get("noisy_count", 0)) + 1
        state["noisy_count"] = n
        if n >= 2:
            return "Still too much noise. I’ll escalate to a dispatcher now.", True, state
        return "I’m getting a lot of noise—could you repeat that clearly once more?", False, state

    if _is_uncoop(latest_user):
        s = int(state.get("short_count", 0)) + 1
        state["short_count"] = s
        if s >= 3:
            return "I’ll let you go and follow up later. Drive safe.", True, state
        return "Could you share your current location and ETA for this load?", False, state

    
    status = _classify_status(latest_user)
    if status and status != state.get("driver_status"):
        state["driver_status"] = status

    if "current_location" not in state:
        loc = extract_location(latest_user)
        if loc: state["current_location"] = loc

    if "eta" not in state:
        eta = extract_eta(latest_user)
        if eta: state["eta"] = eta

    if status in ("Driving","Delayed"):
        if status == "Delayed" and "delay_reason" not in state:
            dr = extract_delay_reason(latest_user)
            if dr: state["delay_reason"] = dr

       
        if "current_location" not in state:
            return "Thanks. What’s your current location? (highway and nearest city)", False, state
        if "eta" not in state:
            ask_count = int(state.get("eta_ask_count", 0)) + 1
            state["eta_ask_count"] = ask_count
            if ask_count >= 2:
                state["eta"] = "Unknown"
                return _confirm_wrap(state)
            return "Got it. What’s your ETA to destination?", False, state
        if status == "Delayed" and "delay_reason" not in state:
            return "Understood. What’s causing the delay—traffic, weather, or something else?", False, state

        return _confirm_wrap(state)

    if status in ("Arrived","Unloading"):
        if "unloading_status" not in state:
            us = extract_unloading(latest_user)
            if us: state["unloading_status"] = us
        if "pod_ack" not in state:
            state["pod_ack"] = False

        if "unloading_status" not in state:
            return "Thanks for the arrival update. What’s the unloading status (door number / waiting for lumper / detention)?", False, state
        if not state.get("pod_ack"):
            state["pod_ack"] = True
            return "Please remember to capture the POD after unload. Acknowledged?", False, state

        return _confirm_wrap(state)

    if not state.get("opened"):
        state["opened"] = True
        return "Hi, this is Dispatch checking on your load. Could you give me a quick status update?", False, state

    return "Thanks. Anything else I should record?", False, state



@router.post("/llm-webhook")
async def llm_webhook_http(request: Request):
    p = await request.json()
    transcript = p.get("transcript") or p.get("history") or []
    latest = p.get("latest_user") or p.get("text") or _latest_user(transcript)
    text, end_call, new_state = draft_reply(latest, p.get("state") or {})
    return {"text": text, "end_call": end_call, "state": new_state}



@router.websocket("/llm-webhook/{call_id}")
async def llm_webhook_ws(ws: WebSocket, call_id: str):
    """
    We accumulate a human-readable transcript and save it to Supabase on end.
    """
    await ws.accept()
    state: dict = {}
    transcript_lines: List[str] = []
    last_idx = 0  

   
    await ws.send_text(json.dumps({
        "response_type": "config",
        "config": {"call_details": True, "auto_reconnect": False, "transcript_with_tool_calls": False},
    }))

    
    await ws.send_text(json.dumps({
        "response_type": "response",
        "response_id": 0,
        "content": "Hi, this is Dispatch. Could you give me a quick status update for your load?",
        "content_complete": True,
        "end_call": False,
    }))

    async def _persist_now(status_val: str | None = None, force_end: bool = False):
        """Save accumulated transcript + summary to Supabase."""
        full = "\n".join(transcript_lines).strip() or None
        summary = summarize_transcript(full or "")
        patch = {
            "transcript": full,
            "structured_payload": summary or {},
        }
        if status_val:
            patch["status"] = status_val
        if force_end:
            patch["status"] = "ended"
        try:
            await _patch_calllog_by_retell(call_id, patch)
            print(f"💾 Saved transcript for {call_id}: {len(full or '')} chars")
        except Exception as e:
            print("⚠️ Failed to save transcript:", e)

    try:
        while True:
            raw = await ws.receive_text()
            try:
                req = json.loads(raw)
            except Exception:
                continue

            interaction_type = (req.get("interaction_type") or "").lower()
            
            tr = req.get("transcript")
            if isinstance(tr, list):
                for utt in tr[last_idx:]:
                    role = (utt.get("role") or "").lower()
                    content = (utt.get("content") or "").strip()
                    if content and role in {"user", "assistant"}:
                        transcript_lines.append(f"{'Driver' if role == 'user' else 'Agent'}: {content}")
                last_idx = len(tr)

            if interaction_type in {"update_only", "call_details", "ping_pong"}:
                
                await _persist_now(status_val="updated")
                continue

            
            latest = _latest_user(tr or [])
            content, end_call, state = draft_reply(latest, state)

            await ws.send_text(json.dumps({
                "response_type": "response",
                "response_id": req.get("response_id"),
                "content": content,
                "content_complete": True,
                "end_call": end_call,
            }))

            
            await _persist_now(status_val="updated", force_end=end_call)

            if end_call:
                await ws.close()
                break

    except WebSocketDisconnect:
       
        await _persist_now(force_end=True)
        return
