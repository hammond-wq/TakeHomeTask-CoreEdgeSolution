from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Any, Dict
from app.vendors.factory import get_vendor

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])

class StartPayload(BaseModel):
    driver_name: str
    load_number: str
    driver_phone: str | None = None
    call_type: str = "web"      
    from_number: str | None = None
    scenario: str | None = None

@router.post("/start")
async def start_voice(payload: StartPayload, vendor: str | None = Query(None, description="retell|pipecat")):
    try:
        v = get_vendor(vendor)
        connect_url, provider_call_id = await v.start(payload.dict())
        return {"connect_url": connect_url, "provider_call_id": provider_call_id, "vendor": (vendor or None)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
