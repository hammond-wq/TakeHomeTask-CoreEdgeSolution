# app/api/v1/routers/results.py  (replace the route)
from fastapi import APIRouter, Query
from app.services.supabase import SupabaseClient

router = APIRouter(prefix="/api/v1/results", tags=["results"])

@router.get("")
async def list_results(load_number: str | None = Query(None), limit: int = 50):
    async with SupabaseClient().client() as c:
        params = {"select": "*", "limit": str(limit), "order": "created_at.desc"}
        if load_number:
            params["load_number"] = f"eq.{load_number}"

        r = await c.get("/calllog", params=params)
        if r.status_code >= 400:
            # Try alternate ordering
            params["order"] = "id.desc"
            r = await c.get("/calllog", params=params)
            if r.status_code >= 400:
                # Last resort: no order
                params.pop("order", None)
                r = await c.get("/calllog", params=params)

        if r.status_code >= 400:
            print("❌ Supabase GET failed:", r.status_code, r.text)
            return []  # avoid blowing up the UI; return empty

        return r.json()
