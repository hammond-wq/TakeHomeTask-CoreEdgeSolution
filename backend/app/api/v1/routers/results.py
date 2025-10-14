# app/api/v1/routers/results.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from app.services.supabase import SupabaseClient

router = APIRouter(prefix="/api/v1/results", tags=["results"])

@router.get("")
async def list_results(load_number: str | None = Query(default=None)):
    params = {"select":"*", "order":"created_at.desc"}
    if load_number:
        params["load_number"] = f"eq.{load_number}"
    async with SupabaseClient().client() as c:
        r = await c.get("/calllog", params=params)
        if r.status_code >= 400:
            raise HTTPException(r.status_code, r.text)
        return r.json()
