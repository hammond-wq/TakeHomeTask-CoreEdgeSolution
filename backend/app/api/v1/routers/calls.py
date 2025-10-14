# app/api/v1/routers/calls.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import os, httpx, time
from app.services.supabase import SupabaseClient

RETELL_API_KEY = os.getenv("RETELL_API_KEY")
RETELL_BASE_URL = os.getenv("RETELL_BASE_URL", "https://api.retellai.com")
RETELL_AGENT_ID = os.getenv("RETELL_AGENT_ID")
RETELL_AGENT_VERSION = int(os.getenv("RETELL_AGENT_VERSION", "1"))

if not RETELL_API_KEY or not RETELL_AGENT_ID:
    raise RuntimeError("Set RETELL_API_KEY and RETELL_AGENT_ID in .env")

router = APIRouter(prefix="/api/v1/calls", tags=["calls"])

class StartCallIn(BaseModel):
    driver_name: str
    driver_phone: str | None = None  # for phone calls
    load_number: str
    call_type: str = "web"           # "web" or "phone"
    from_number: str | None = None   # required if call_type="phone"

def retell_headers():
    return {
        "Authorization": f"Bearer {RETELL_API_KEY}",
        "Content-Type": "application/json",
    }

@router.post("/start")
async def start_call(payload: StartCallIn, request: Request):
    """
    Creates web call (default) for testing outside US; switch to phone by call_type="phone".
    Saves a calllog row with provider_call_id for correlation.
    """
    # 1) Create a calllog row (pending)
    provider_call_id = f"retell_{int(time.time()*1000)}"
    async with SupabaseClient().client() as c:
        create_log = {
            "agent_id": 0,  # optional if you don't map to table agent.id yet
            "driver_id": 0, # optional (or manage drivers table separately)
            "load_number": payload.load_number,
            "call_outcome": None,
            "provider_call_id": provider_call_id,
            "structured_payload": {},
        }
        _ = await c.post("/calllog", json=create_log)  # ignore response for now

    # 2) Call Retell
    base_url = f"{RETELL_BASE_URL}/v2" if "retellai.com" in RETELL_BASE_URL else RETELL_BASE_URL
    async with httpx.AsyncClient(base_url=base_url, headers=retell_headers(), timeout=30.0) as rc:
        if payload.call_type == "phone":
            # Phone call (requires numbers)
            if not (payload.driver_phone and payload.from_number):
                raise HTTPException(400, "driver_phone and from_number required for phone calls")
            data = {
                "agent_id": RETELL_AGENT_ID,
                "agent_version": RETELL_AGENT_VERSION,
                "to_number": payload.driver_phone,
                "from_number": payload.from_number,
                "metadata": {"load_number": payload.load_number, "provider_call_id": provider_call_id},
                "retell_llm_dynamic_variables": {"driver_name": payload.driver_name, "load_number": payload.load_number},
                "call_type": "phone_call"
            }
            r = await rc.post("/create-phone-call", json=data)
        else:
            # Web call (works outside US) – client will connect by call_id to Retell Web SDK
            data = {
                "agent_id": RETELL_AGENT_ID,
                "agent_version": RETELL_AGENT_VERSION,
                "metadata": {"load_number": payload.load_number, "provider_call_id": provider_call_id},
                "retell_llm_dynamic_variables": {"driver_name": payload.driver_name, "load_number": payload.load_number}
            }
            r = await rc.post("/create-web-call", json=data)
        if r.status_code >= 400:
            raise HTTPException(r.status_code, r.text)
        call = r.json()
        # call contains call_id, status, transcript fields after end (for web it appears after)
        return {"provider_call_id": provider_call_id, "retell": call}
