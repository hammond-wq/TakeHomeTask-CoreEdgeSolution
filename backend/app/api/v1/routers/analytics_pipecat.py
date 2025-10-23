from fastapi import APIRouter, HTTPException
from app.services.supabase import SupabaseClient

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

@router.get("/pipecat")
async def get_pipecat_analytics():
 
    query = """
        select
            count(*) as total_calls,
            avg( (extra->>'duration_secs')::numeric ) as avg_duration,
            count(*) filter (where structured_payload->>'call_outcome' = 'Emergency Escalation') as emergencies,
            count(*) filter (where structured_payload->>'call_outcome' = 'In-Transit Update') as normal_updates
        from calllog
        where provider_call_id like 'pipecat_%';
    """
    try:
        async with SupabaseClient().client() as c:
            r = await c.rpc("exec_sql", {"sql": query}) if hasattr(c, "rpc") else await c.get("/custom", params={"sql": query})
            return r.json() if hasattr(r, "json") else r
    except Exception as e:
        raise HTTPException(500, f"Analytics query failed: {e}")
