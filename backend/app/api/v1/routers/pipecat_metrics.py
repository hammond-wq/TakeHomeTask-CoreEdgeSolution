from fastapi import APIRouter, HTTPException
from app.services.supabase import SupabaseClient

router = APIRouter(prefix="/api/v1/pipecat", tags=["pipecat"])

@router.get("/metrics")
async def get_pipecat_metrics():
    """
    Returns summarized Pipecat analytics from calllog.extra JSON column.
    Used by the frontend analytics dashboard.
    """
    async with SupabaseClient().client() as c:
        res = await c.get("/calllog", params={
            "select": "id,driver_id,load_number,created_at,extra",
            "order": "created_at.desc",
            "limit": 50,
        })
        if res.status_code >= 400:
            raise HTTPException(res.status_code, res.text)

        rows = res.json()
        metrics = []
        for row in rows:
            extra = row.get("extra") or {}
            metrics.append({
                "id": row.get("id"),
                "driver_id": row.get("driver_id"),
                "load_number": row.get("load_number"),
                "created_at": row.get("created_at"),
                "duration_secs": extra.get("duration_secs", 0),
                "interruptions_est": extra.get("interruptions_est", 0),
                "tokens_estimated": extra.get("tokens_estimated", 0),
                "keyword_hits": extra.get("keyword_hits", {}),
            })
        return {"items": metrics}
