# app/api/v1/routers/dev_diag.py
from fastapi import APIRouter
from app.services.supabase import SupabaseClient
import time

router = APIRouter(prefix="/api/v1/dev", tags=["dev"])

@router.post("/seed-calllog")
async def seed_calllog():
    provider = f"debug_{int(time.time()*1000)}"
    async with SupabaseClient().client() as c:
        r = await c.post("/calllog", json={
            "provider_call_id": provider,
            "load_number": "LDN-DEBUG",
            "status": "initiated",
            "structured_payload": {},
        })
        body = r.json() if r.headers.get("content-type","").startswith("application/json") else r.text
        return {"status": r.status_code, "body": body, "provider_call_id": provider}

@router.get("/show-calllog")
async def show_calllog():
    async with SupabaseClient().client() as c:
        r = await c.get("/calllog", params={"select":"*", "order":"id.desc", "limit":"5"})
        return {"status": r.status_code, "rows": r.json()}
