from typing import Sequence
from app.domain.interfaces.agent_repo import AgentRepository
from app.domain.entities.agent import Agent

class AgentService:
    def __init__(self, repo: AgentRepository):
        self.repo = repo

    async def create_agent(self, *, name:str, language:str, voice_type:str) -> Agent:
        return await self.repo.create(name=name, language=language, voice_type=voice_type)

    async def list_agents(self) -> Sequence[Agent]:
        return await self.repo.list()

    async def activate(self, agent_id:int, active:bool) -> Agent:
        return await self.repo.update_status(agent_id, active)
