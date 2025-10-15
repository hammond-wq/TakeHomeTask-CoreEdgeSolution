# app/services/supabase.py
from __future__ import annotations
import httpx
from contextlib import asynccontextmanager
from app.core.config import settings

class SupabaseClient:
    def __init__(self):
        self.base_url = settings.supabase_url.rstrip("/") + "/rest/v1"
        self.headers = {
            "apikey": settings.supabase_service_key,
            "Authorization": f"Bearer {settings.supabase_service_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            
            "Prefer": "return=representation",
        }

    @asynccontextmanager
    async def client(self):
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=30.0
        ) as c:
            yield c
