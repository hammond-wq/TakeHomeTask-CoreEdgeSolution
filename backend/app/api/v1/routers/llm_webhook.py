from __future__ import annotations

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
import json
from typing import List, Tuple
from app.services.calllog_repo import CallLogRepo
from app.services.postprocess import summarize_transcript
from ._retell_common import (
    classify_status, detect_emergency, is_noisy, is_uncoop,
    extract_location, extract_eta, extract_delay_reason, extract_unloading,
    latest_user,
)

router = APIRouter(prefix="/api/v1/retell", tags=["retell"])

async def _patch_calllog_by_retell(retell_call_id: str, patch: dict) -> None:
    if not retell_call_id:
        return
    ok = await CallLogRepo.patch_by_retell(retell_call_id, patch)
    if not ok:
        print("Failed to patch calllog for retell_call_id", retell_call_id)

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

def draft_reply(latest_user_text: str, state: dict) -> tuple[str, bool, dict]:
    emerg = detect_emergency(latest_user_text)
    if emerg:
        state.update({"scenario":"Emergency","emergency_type":emerg})
        return (
            "I’m sorry to hear that. Are you safe? Any injuries? Please share exact location and whether the load is secure. I’m connecting you to a dispatcher now.",
            False,
            state
        )

    if is_noisy(latest_user_text):
        n = int(state.get("noisy_count", 0)) + 1
        state["noisy_count"] = n
        if n >= 2:
            return "Still too much noise. I’ll escalate to a dispatcher now.", True, state
        return "I’m getting a lot of noise—could you repeat that clearly once more?", False, state

    if is_uncoop(latest_user_text):
        s = int(state.get("short_count", 0)) + 1
        state["short_count"] = s
        if s >= 3:
            return "I’ll let you go and follow up later. Drive safe.", True, state
        return "Could you share your current location and ETA for this load?", False, state

    status = classify_status(latest_user_text)
    if status and status != state.get("driver_status"):
        state["driver_status"] = status

    if "current_location" not in state:
        loc = extract_location(latest_user_text)
        if loc: state["current_location"] = loc

    if "eta" not in state:
        eta = extract_eta(latest_user_text)
        if eta: state["eta"] = eta

    if status in ("Driving","Delayed"):
        if status == "Delayed" and "delay_reason" not in state:
            dr = extract_delay_reason(latest_user_text)
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
            us = extract_unloading(latest_user_text)
            if us: state["unloading_status"] = us
        if "pod_ack" not in state:
            state["pod_ack"] = False

        if "unloading_status" not in state:
            return "Thanks for the arrival update. What’s the unloading status (door number / waiting for lumper / detention)?", False, state
        if not state.get("pod_ack"):
            state["pod_ack"] = True
            return "Please remember to capture the POD after unload. A acknowledged?", False, state

        return _confirm_wrap(state)

    if not state.get("opened"):
        state["opened"] = True
        return "Hi, this is Dispatch checking on your load. Could you give me a quick status update?", False, state

    return "Thanks. Anything else I should record?", False, state

@router.post("/llm-webhook")
async def llm_webhook_http(request: Request):
    p = await request.json()
    transcript = p.get("transcript") or p.get("history") or []
    latest = p.get("latest_user") or p.get("text") or latest_user(transcript)
    text, end_call, new_state = draft_reply(latest, p.get("state") or {})
    return {"text": text, "end_call": end_call, "state": new_state}

@router.websocket("/llm-webhook/{call_id}")
async def llm_webhook_ws(ws: WebSocket, call_id: str):
    """
    Accumulates a human-readable transcript and saves it to Supabase on end.
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
        full = "\n".join(transcript_lines).strip() or None
        summary = summarize_transcript(full or "")
        patch = {"transcript": full, "structured_payload": summary or {}}
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

            latest_txt = latest_user(tr or [])
            content, end_call, state = draft_reply(latest_txt, state)

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
