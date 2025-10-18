from __future__ import annotations
from typing import Tuple, Mapping, Any
from app.api.v1.routers.calls import retell_headers, CREATE_WEB_CALL_URL, CREATE_PHONE_CALL_URL, \
    RETELL_AGENT_ID, RETELL_AGENT_VERSION
import httpx, time

class RetellVendor:
    async def start(self, payload: Mapping[str, Any]) -> Tuple[str, str]:
       
        provider_call_id = f"retell_{int(time.time() * 1000)}"
        dyn_vars = {
            "driver_name": payload.get("driver_name"),
            "load_number": payload.get("load_number"),
        }
        if payload.get("driver_phone"):
            dyn_vars["driver_phone"] = payload["driver_phone"]

        metadata = {"load_number": payload.get("load_number"), "provider_call_id": provider_call_id}

        is_phone = (payload.get("call_type","web").lower() == "phone")
        req_body = {
            "agent_id": RETELL_AGENT_ID,
            "agent_version": RETELL_AGENT_VERSION,
            "metadata": metadata,
            "retell_llm_dynamic_variables": dyn_vars,
        }
        url = CREATE_PHONE_CALL_URL if is_phone else CREATE_WEB_CALL_URL
        if is_phone:
            req_body["to_number"] = payload["driver_phone"]
            req_body["from_number"] = payload["from_number"]

        async with httpx.AsyncClient(headers=retell_headers(), timeout=30.0) as rc:
            r = await rc.post(url, json=req_body)
            r.raise_for_status()
            call = r.json()

        
        connect_url = call.get("web_call_url") or ""
        return connect_url, provider_call_id
