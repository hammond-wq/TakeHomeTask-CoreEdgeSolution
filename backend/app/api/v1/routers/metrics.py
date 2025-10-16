from fastapi import APIRouter
from app.services.supabase import SupabaseClient

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

@router.get("")
async def get_metrics():
    async with SupabaseClient().client() as c:
        r = await c.get("/calllog", params={"select": "*"})
        data = r.json()

    def sp(d, *path, default=None):
        cur = d
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                return default
        return cur

    total_calls = len(data)
    arrivals = sum(1 for d in data if sp(d, "structured_payload", "driver_status") == "Arrived")
    delays = sum(1 for d in data if sp(d, "structured_payload", "driver_status") == "Delayed")
    emergencies = sum(1 for d in data if sp(d, "structured_payload", "scenario") == "Emergency")
    delay_sum = sum(int(sp(d, "structured_payload", "delay_minutes", default=0) or 0) for d in data)
    avg_delay = round(delay_sum / (delays or 1), 2)

    return {
        "total_calls": total_calls,
        "arrivals": arrivals,
        "delays": delays,
        "emergencies": emergencies,
        "avg_delay_minutes": avg_delay,
    }
