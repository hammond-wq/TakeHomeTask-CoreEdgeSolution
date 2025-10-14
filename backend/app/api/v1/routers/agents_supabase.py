# app/api/v1/routers/agents_supabase.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.supabase import SupabaseClient

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

class AgentIn(BaseModel):
    name: str
    language: str
    voice_type: str
    active: bool = True

@router.get("")
async def list_agents():
    async with SupabaseClient().client() as c:
        r = await c.get("/agent", params={"select":"*", "order":"created_at.desc"})
        r.raise_for_status()
        return r.json()

@router.post("")
async def create_agent(agent: AgentIn):
    async with SupabaseClient().client() as c:
        r = await c.post("/agent", json=agent.dict())
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        data = r.json()
        return data[0] if isinstance(data, list) and data else data
