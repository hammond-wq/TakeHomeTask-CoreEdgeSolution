from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db.session import get_session
from app.infrastructure.repositories.agent_repo_sql import SQLAgentRepository
from app.infrastructure.repositories.call_repo_sql import SQLCallRepository
from app.infrastructure.external.retell_http import RetellHTTPClient
from app.services.agent_service import AgentService
from app.services.call_service import CallService

def agent_service(session: AsyncSession = Depends(get_session)) -> AgentService:
    return AgentService(SQLAgentRepository(session))

def call_service(session: AsyncSession = Depends(get_session)) -> CallService:
    return CallService(SQLCallRepository(session), RetellHTTPClient())
