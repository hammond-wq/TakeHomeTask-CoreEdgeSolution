from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Sequence, Optional, Mapping, Any
from app.domain.entities.call_log import CallLog

class SQLCallRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_log(self, *, agent_id:int, driver_id:int|None, load_number:str, provider_call_id:str|None, call_outcome:str="queued", structured_payload:Mapping[str,Any]|None=None) -> CallLog:
        obj = CallLog(agent_id=agent_id, driver_id=driver_id, load_number=load_number, provider_call_id=provider_call_id, call_outcome=call_outcome, structured_payload=structured_payload)  # type: ignore
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def get(self, call_id:int) -> Optional[CallLog]:
        res = await self.session.execute(select(CallLog).where(CallLog.id==call_id))
        return res.scalar_one_or_none()

    async def list_recent(self, limit:int=50) -> Sequence[CallLog]:
        res = await self.session.execute(select(CallLog).order_by(CallLog.id.desc()).limit(limit))
        return list(res.scalars().all())

    async def update_status(self, call_id:int, *, call_outcome:str) -> CallLog:
        await self.session.execute(update(CallLog).where(CallLog.id==call_id).values(call_outcome=call_outcome))
        await self.session.commit()
        obj = await self.get(call_id)
        assert obj
        return obj

    async def attach_structured_payload(self, call_id:int, *, payload:Mapping[str,Any]) -> CallLog:
        await self.session.execute(update(CallLog).where(CallLog.id==call_id).values(structured_payload=payload))
        await self.session.commit()
        obj = await self.get(call_id)
        assert obj
        return obj
