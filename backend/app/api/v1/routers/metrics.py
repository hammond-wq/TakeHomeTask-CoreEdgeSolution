from fastapi import APIRouter
from app.services.supabase import SupabaseClient

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

@router.get("")
async def get_metrics():
    async with SupabaseClient().client() as c:
        r = await c.get("/calllog", params={"select": "*"})
        data = r.json()
        total_calls = len(data)
        arrivals = sum(1 for d in data if d["structured_payload"].get("driver_status") == "Arrived")
        delays = sum(1 for d in data if d["structured_payload"].get("driver_status") == "Delayed")
        emergencies = sum(1 for d in data if d["structured_payload"].get("scenario") == "Emergency")
        avg_delay = (
            sum(int(d["structured_payload"].get("delay_minutes", 0) or 0) for d in data) /
            (delays or 1)
        )

        return {
            "total_calls": total_calls,
            "arrivals": arrivals,
            "delays": delays,
            "emergencies": emergencies,
            "avg_delay_minutes": round(avg_delay, 2)
        }
