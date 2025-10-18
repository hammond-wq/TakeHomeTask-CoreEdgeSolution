from __future__ import annotations
from typing import Tuple, Mapping, Any
import time, urllib.parse as up
from app.core.config import settings
from app.services.calllog_repo import CallLogRepo
from app.services.agents_repo import AgentsRepo
from app.services.drivers_repo import DriversRepo

class PipecatVendor:
    async def start(self, payload: Mapping[str, Any]) -> Tuple[str, str]:
        """
        Create a calllog row now (status=initiated), return client URL
        Pipecat client reads ?conv=<provider_call_id> and the bot will later POST finalize to backend.
        """
        provider_call_id = f"pipecat_{int(time.time()*1000)}"

        
        agent_db_id  = await AgentsRepo.ensure_agent_id()
        driver_db_id = await DriversRepo.ensure_driver_id(payload.get("driver_name"), payload.get("driver_phone"))

        
        await CallLogRepo.post({
            "provider_call_id": provider_call_id,
            "load_number": payload.get("load_number"),
            "status": "initiated",
            "structured_payload": {},
            "agent_id": agent_db_id,
            "driver_id": driver_db_id,
            "scenario": payload.get("scenario") or "Dispatch",
        })

        q = up.urlencode({"conv": provider_call_id})
        connect_url = f"{settings.pipecat_client_url.rstrip('/')}/?{q}"
        return connect_url, provider_call_id
