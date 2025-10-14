# app/api/v1/routers/retell_webhook.py
from __future__ import annotations
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.services.postprocess import summarize_transcript
from app.services.supabase import SupabaseClient

router = APIRouter(prefix="/api/v1/retell", tags=["retell"])

@router.post("/webhook")
async def retell_webhook(request: Request):
    payload = await request.json()
    # Retell sends various event types; we care when transcript is present
    event = payload.get("event") or payload.get("type")
    call = payload.get("call") or payload  # some payloads nest under "call"
    provider_call_id = call.get("metadata", {}).get("provider_call_id") or call.get("call_id")

    # Use available transcript fields (depends on call lifecycle)
    transcript = call.get("transcript") or ""
    if not transcript and call.get("transcript_object"):
        # Flatten minimal
        transcript = "\n".join([f'{u.get("role","Agent")}: {u.get("content","")}' for u in call["transcript_object"]])

    # If no transcript yet (e.g., call_started), just ack
    if not transcript:
        return JSONResponse({"status":"ok", "note":"no transcript yet", "event": event})

    summary = summarize_transcript(transcript)

    # Save to Supabase calllog
    async with SupabaseClient().client() as c:
        # Update by provider_call_id
        r = await c.patch(
            "/calllog",
            params={"provider_call_id": f"eq.{provider_call_id}"},
            json={"structured_payload": summary, "call_outcome": summary.get("call_outcome")}
        )
        # If no row matched (PATCH returns []), insert instead
        if r.status_code == 204:
            await c.post("/calllog", json={
                "load_number": call.get("metadata", {}).get("load_number"),
                "provider_call_id": provider_call_id,
                "call_outcome": summary.get("call_outcome"),
                "structured_payload": summary
            })

    return {"status":"processed", "event": event, "provider_call_id": provider_call_id}
