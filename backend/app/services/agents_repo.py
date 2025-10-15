from __future__ import annotations
from app.services.supabase import SupabaseClient

AGENTS_PATH = "/agent"  

class AgentsRepo:
    @staticmethod
    async def ensure_agent_id() -> int:
        """Return an integer id from public.agent; create a 'Custom LLM agent' if table is empty."""
        async with SupabaseClient().client() as c:
            
            r = await c.get(AGENTS_PATH, params={"select":"id", "order":"id.asc", "limit":"1"})
            if r.status_code < 400:
                rows = r.json() or []
                if rows and isinstance(rows[0].get("id"), int):
                    return int(rows[0]["id"])

            
            r2 = await c.post(AGENTS_PATH, json={"name": "Custom LLM agent"})
            if r2.status_code >= 400:
                
                return 1
            rows2 = r2.json() or []
            if rows2 and isinstance(rows2[0].get("id"), int):
                return int(rows2[0]["id"])
            return 1
