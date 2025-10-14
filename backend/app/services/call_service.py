from typing import Sequence, Mapping, Any
from app.domain.interfaces.call_repo import CallRepository
from app.domain.interfaces.retell_client import RetellClient
from app.domain.entities.call_log import CallLog

class CallService:
    def __init__(self, repo: CallRepository, dialer: RetellClient):
        self.repo = repo
        self.dialer = dialer

    async def trigger(self, *, to_number:str, agent_id:int, load_number:str, agent_config:Mapping[str,Any], context:Mapping[str,Any]) -> CallLog:
        ret = await self.dialer.trigger_call(to_number=to_number, agent_config=agent_config, context=context)
        provider_id = str(ret.get("id", "pending"))
        log = await self.repo.create_log(agent_id=agent_id, driver_id=None, load_number=load_number, provider_call_id=provider_id, call_outcome=ret.get("status", "queued"))
        return log

    async def recent(self, limit:int=50) -> Sequence[CallLog]:
        return await self.repo.list_recent(limit=limit)
