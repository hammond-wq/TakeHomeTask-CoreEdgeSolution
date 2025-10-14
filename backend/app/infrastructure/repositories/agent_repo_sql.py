from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.entities.agent import Agent
from typing import Sequence, Optional

class SQLAgentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, name, language, voice_type, active=True) -> Agent:
        obj = Agent(name=name, language=language, voice_type=voice_type, active=active)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def get(self, agent_id:int) -> Optional[Agent]:
        res = await self.session.execute(select(Agent).where(Agent.id==agent_id))
        return res.scalar_one_or_none()

    async def list(self) -> Sequence[Agent]:
        res = await self.session.execute(select(Agent).order_by(Agent.id.desc()))
        return list(res.scalars().all())

    async def update_status(self, agent_id:int, active:bool) -> Agent:
        await self.session.execute(update(Agent).where(Agent.id==agent_id).values(active=active))
        await self.session.commit()
        obj = await self.get(agent_id)
        assert obj
        return obj
