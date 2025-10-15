from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.services.supabase import SupabaseClient

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

class AgentIn(BaseModel):
    name: str
    language: Optional[str] = None
    voice_type: Optional[str] = None
    active: bool = True
    system_prompt: Optional[str] = None
    emergency_triggers: List[str] = Field(default_factory=list)
    behavior: Dict[str, Any] = Field(default_factory=dict)  
    voice_preset: Optional[str] = None

@router.get("")
async def list_agents():
    async with SupabaseClient().client() as c:
        r = await c.get("/agent", params={"order": "created_at.desc"})
        r.raise_for_status()
        return r.json()

@router.post("")
async def create_agent(body: AgentIn):
    async with SupabaseClient().client() as c:
        r = await c.post("/agent", json=body.dict())
        if r.status_code >= 400:
            raise HTTPException(r.status_code, r.text)
        return r.json()[0]

@router.get("/{agent_id}")
async def get_agent(agent_id: int):
    async with SupabaseClient().client() as c:
        r = await c.get("/agent", params={"id": f"eq.{agent_id}"})
        r.raise_for_status()
        data = r.json()
        if not data: raise HTTPException(404, "not found")
        return data[0]

@router.put("/{agent_id}")
async def update_agent(agent_id: int, body: AgentIn):
    async with SupabaseClient().client() as c:
        r = await c.patch("/agent", params={"id": f"eq.{agent_id}"}, json=body.dict())
        if r.status_code >= 400:
            raise HTTPException(r.status_code, r.text)
        return r.json()[0]
