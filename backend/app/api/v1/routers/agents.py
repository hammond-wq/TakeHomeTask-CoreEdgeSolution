from fastapi import APIRouter, Depends
from app.api.v1.dependencies import agent_service
from app.services.agent_service import AgentService
from app.schemas.agent import AgentCreate, AgentOut

router = APIRouter()

@router.post("/agents", response_model=AgentOut)
async def create_agent(payload: AgentCreate, svc: AgentService = Depends(agent_service)):
    obj = await svc.create_agent(name=payload.name, language=payload.language, voice_type=payload.voice_type)
    return AgentOut.model_validate(obj.__dict__)

@router.get("/agents", response_model=list[AgentOut])
async def list_agents(svc: AgentService = Depends(agent_service)):
    items = await svc.list_agents()
    return [AgentOut.model_validate(i.__dict__) for i in items]
