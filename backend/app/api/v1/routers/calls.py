# app/api/v1/routers/calls.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import os, httpx, time
from app.services.supabase import SupabaseClient

router = APIRouter(prefix="/api/v1/calls", tags=["calls"])

# ─────────────────────────────────────────────
# Retell config (HARD-CODED FOR DEV)
# Use your SERVER-SIDE API SECRET KEY here (NOT publishable key, NOT webhook secret)
# ─────────────────────────────────────────────
RETELL_API_KEY = "key_999b02121954289e1f248d730285"   # <-- your secret API key
RETELL_BASE     = "https://api.retellai.com"          # don't add /v2 here
RETELL_AGENT_ID = "agent_9cdfafda6777ef1353256d0da2"  # <-- your agent id
RETELL_AGENT_VERSION = 1

if not RETELL_API_KEY or not RETELL_AGENT_ID:
    raise RuntimeError("RETELL_API_KEY and RETELL_AGENT_ID are required")

CREATE_WEB_CALL_URL   = f"{RETELL_BASE}/v2/create-web-call"
CREATE_PHONE_CALL_URL = f"{RETELL_BASE}/v2/create-phone-call"

# ─────────────────────────────────────────────
# Request schema
# ─────────────────────────────────────────────
class StartCallIn(BaseModel):
    driver_name: str
    driver_phone: str | None = None   # required for phone calls
    load_number: str
    call_type: str = "web"            # "web" or "phone"
    from_number: str | None = None    # required if call_type="phone"

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def retell_headers() -> dict:
    # REQUIRED AUTH HEADER per Retell docs
    return {
        "Authorization": f"Bearer {RETELL_API_KEY}",
        "Content-Type": "application/json",
    }

async def create_supabase_calllog(provider_call_id: str, load_number: str) -> None:
    async with SupabaseClient().client() as c:
        payload = {
            "agent_id": 0,
            "driver_id": 0,
            "load_number": load_number,
            "call_outcome": None,
            "provider_call_id": provider_call_id,
            "structured_payload": {},
        }
        try:
            await c.post("/calllog", json=payload)
        except Exception as e:
            # Don't block Retell call if logging fails
            print("⚠️ Supabase calllog insert failed:", e)

# ─────────────────────────────────────────────
# Main endpoint
# ─────────────────────────────────────────────
@router.post("/start")
async def start_call(payload: StartCallIn, request: Request):
    """
    Creates a Retell web or phone call and logs a pending call in Supabase.

    • Web call → returns { call_id, access_token } for frontend to join via Retell Web SDK.
    • Phone call → dials PSTN (from_number → to_number).
    """
    provider_call_id = f"retell_{int(time.time() * 1000)}"
    await create_supabase_calllog(provider_call_id, payload.load_number)

    async with httpx.AsyncClient(headers=retell_headers(), timeout=30.0) as rc:
        if payload.call_type.lower() == "phone":
            # Validate phone requirements
            if not payload.driver_phone or not payload.from_number:
                raise HTTPException(
                    status_code=400,
                    detail="driver_phone and from_number are required for phone calls",
                )

            req_body = {
                "agent_id": RETELL_AGENT_ID,
                "agent_version": RETELL_AGENT_VERSION,
                "to_number": payload.driver_phone,
                "from_number": payload.from_number,
                "metadata": {
                    "load_number": payload.load_number,
                    "provider_call_id": provider_call_id,
                },
                "retell_llm_dynamic_variables": {
                    "driver_name": payload.driver_name,
                    "load_number": payload.load_number,
                }
            }

            print(f"📞 POST {CREATE_PHONE_CALL_URL}")
            print("   Body:", req_body)
            r = await rc.post(CREATE_PHONE_CALL_URL, json=req_body)

        else:
            # WEB CALL (browser-based)
            req_body = {
                "agent_id": RETELL_AGENT_ID,
                "agent_version": RETELL_AGENT_VERSION,
                "metadata": {
                    "load_number": payload.load_number,
                    "provider_call_id": provider_call_id,
                },
                "retell_llm_dynamic_variables": {
                    "driver_name": payload.driver_name,
                    "load_number": payload.load_number,
                }
            }

            print(f"💻 POST {CREATE_WEB_CALL_URL}")
            print("   Body:", req_body)
            r = await rc.post(CREATE_WEB_CALL_URL, json=req_body)

        # Handle Retell errors explicitly
        if r.status_code >= 400:
            print("❌ Retell error:", r.status_code, r.text)
            raise HTTPException(status_code=r.status_code, detail=r.text)

        call = r.json()
        print("✅ Retell call created:", call)

        # Return correlation id + Retell payload (web call includes call_id & access_token)
        return {"provider_call_id": provider_call_id, "retell": call}
