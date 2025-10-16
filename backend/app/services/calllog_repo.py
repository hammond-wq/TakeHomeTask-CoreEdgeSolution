from __future__ import annotations
from typing import Mapping, Any
from app.services.supabase import SupabaseClient

class CallLogRepo:
    PATH = "/calllog"

    @staticmethod
    async def post(row: Mapping[str, Any]) -> None:
        async with SupabaseClient().client() as c:
            r = await c.post(CallLogRepo.PATH, json=row)
            r.raise_for_status()

    @staticmethod
    async def patch_by_provider(provider_call_id: str, patch: Mapping[str, Any]) -> bool:
        if not provider_call_id:
            return False
        async with SupabaseClient().client() as c:
            r = await c.patch(CallLogRepo.PATH, params={"provider_call_id": f"eq.{provider_call_id}"}, json=patch)
            return r.status_code < 400

    @staticmethod
    async def patch_by_retell(retell_call_id: str, patch: Mapping[str, Any]) -> bool:
        if not retell_call_id:
            return False
        async with SupabaseClient().client() as c:
            r = await c.patch(CallLogRepo.PATH, params={"retell_call_id": f"eq.{retell_call_id}"}, json=patch)
            return r.status_code < 400
