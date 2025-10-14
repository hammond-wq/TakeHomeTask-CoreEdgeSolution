from typing import Protocol, Mapping, Any

class RetellClient(Protocol):
    async def trigger_call(self, *, to_number:str, agent_config:Mapping[str, Any], context:Mapping[str,Any]) -> dict: ...
