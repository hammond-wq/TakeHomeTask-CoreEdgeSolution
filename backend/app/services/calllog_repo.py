from __future__ import annotations
from typing import Any, Dict, Optional
from app.services.supabase import SupabaseClient

class CallLogRepo:
    @staticmethod
    async def post(row: Dict[str, Any]) -> bool:
        async with SupabaseClient().client() as c:
            r = await c.post("/calllog", json=[row])
            return r.status_code < 400

    @staticmethod
    async def patch_by_provider(provider_call_id: str, patch: Dict[str, Any]) -> bool:
        async with SupabaseClient().client() as c:
            r = await c.patch(f"/calllog?provider_call_id=eq.{provider_call_id}", json=patch)
            return r.status_code < 400

    @staticmethod
    async def get_by_provider(provider_call_id: str) -> Optional[Dict[str, Any]]:
        async with SupabaseClient().client() as c:
            r = await c.get("/calllog", params={"provider_call_id": f"eq.{provider_call_id}", "limit": "1"})
            if r.status_code >= 400:
                return None
            rows = r.json() or []
            return rows[0] if rows else None
