# app/api/v1/routers/calls.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import httpx, time

from app.core.config import settings
from app.services.supabase import SupabaseClient
from app.services.agents_repo import AgentsRepo
from app.services.drivers_repo import DriversRepo

router = APIRouter(prefix="/api/v1/calls", tags=["calls"])

RETELL_API_KEY       = settings.retell_api_key
RETELL_BASE          = settings.retell_base_url.rstrip("/") or "https://api.retellai.com"
RETELL_AGENT_ID      = settings.retell_agent_id
RETELL_AGENT_VERSION = settings.retell_agent_version or 1

if not RETELL_API_KEY or not RETELL_AGENT_ID:
    raise RuntimeError("RETELL_API_KEY and RETELL_AGENT_ID are required")

CREATE_WEB_CALL_URL   = f"{RETELL_BASE}/v2/create-web-call"
CREATE_PHONE_CALL_URL = f"{RETELL_BASE}/v2/create-phone-call"


class StartCallIn(BaseModel):
    driver_name: str
    driver_phone: str | None = None  
    load_number: str
    call_type: str = "web"           
    from_number: str | None = None   


def retell_headers() -> dict:
    return {
        "Authorization": f"Bearer {RETELL_API_KEY}",
        "Content-Type": "application/json",
    }


async def create_supabase_calllog(
    provider_call_id: str,
    load_number: str,
    driver_name: str | None,
    driver_phone: str | None,
) -> None:
    agent_db_id = await AgentsRepo.ensure_agent_id()             
    driver_db_id = await DriversRepo.ensure_driver_id(driver_name, driver_phone)  
    print(f"🆔 Using agent_id={agent_db_id}, driver_id={driver_db_id} for calllog insert")

    async with SupabaseClient().client() as c:
        payload = {
            "provider_call_id": provider_call_id,
            "load_number": load_number,
            "status": "initiated",
            "structured_payload": {},
            "agent_id": agent_db_id,
            "driver_id": driver_db_id,
        }
        r = await c.post("/calllog", json=payload)
        try:
            data = r.json()
        except Exception:
            data = r.text
        print("↪️  INSERT /calllog", r.status_code, data)


async def _update_supabase_calllog(provider_call_id: str, patch: dict) -> None:
    async with SupabaseClient().client() as c:
        params = {"provider_call_id": f"eq.{provider_call_id}"}
        r = await c.patch("/calllog", params=params, json=patch)
        try:
            data = r.json()
        except Exception:
            data = r.text
        print("↪️  PATCH /calllog by provider_call_id", r.status_code, data)


@router.post("/start")
async def start_call(payload: StartCallIn, request: Request):
    """
    Creates a Retell web or phone call and logs a pending call in Supabase.
    """
    provider_call_id = f"retell_{int(time.time() * 1000)}"

    
    await create_supabase_calllog(
        provider_call_id,
        payload.load_number,
        payload.driver_name,
        payload.driver_phone,
    )

    
    dyn_vars: dict[str, str] = {
        "driver_name": payload.driver_name,
        "load_number": payload.load_number,
    }
    if payload.driver_phone and payload.driver_phone.strip():
        dyn_vars["driver_phone"] = payload.driver_phone.strip()

    metadata = {
        "load_number": payload.load_number,
        "provider_call_id": provider_call_id,
    }

    if payload.call_type.lower() == "phone":
        
        if not (payload.driver_phone and payload.driver_phone.strip()) or not (payload.from_number and payload.from_number.strip()):
            raise HTTPException(
                status_code=400,
                detail="driver_phone and from_number are required for phone calls",
            )

        req_body = {
            "agent_id": RETELL_AGENT_ID,
            "agent_version": RETELL_AGENT_VERSION,
            "to_number": payload.driver_phone.strip(),
            "from_number": payload.from_number.strip(),
            "metadata": metadata,
            "retell_llm_dynamic_variables": dyn_vars,
        }
        url = CREATE_PHONE_CALL_URL
        print(f"📞 POST {url}")
        print("   Body:", req_body)
    else:
        req_body = {
            "agent_id": RETELL_AGENT_ID,
            "agent_version": RETELL_AGENT_VERSION,
            "metadata": metadata,
            "retell_llm_dynamic_variables": dyn_vars,
        }
        url = CREATE_WEB_CALL_URL
        print(f"💻 POST {url}")
        print("   Body:", req_body)

    async with httpx.AsyncClient(headers=retell_headers(), timeout=30.0) as rc:
        r = await rc.post(url, json=req_body)
        if r.status_code >= 400:
            print("❌ Retell error:", r.status_code, r.text)
            raise HTTPException(status_code=r.status_code, detail=r.text)
        call = r.json()

    
    try:
        await _update_supabase_calllog(provider_call_id, {"retell_call_id": call.get("call_id")})
    except Exception as e:
        print("⚠️ Supabase calllog update failed:", e)

    print("✅ Retell call created:", call)
    return {"provider_call_id": provider_call_id, "retell": call}
