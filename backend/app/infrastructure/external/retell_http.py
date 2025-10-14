import httpx
from typing import Mapping, Any
from app.core.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential

class RetellHTTPClient:
    def __init__(self, api_key:str|None=None, base_url:str|None=None):
        self.api_key = api_key or settings.retell_api_key
        self.base_url = base_url or settings.retell_base_url
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=4))
    async def trigger_call(self, *, to_number:str, agent_config:Mapping[str, Any], context:Mapping[str,Any]) -> dict:
        payload = {"to": to_number, "agent": agent_config, "context": context}
        async with httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=20) as client:
            r = await client.post("/v1/calls", json=payload)
            r.raise_for_status()
            return r.json()
