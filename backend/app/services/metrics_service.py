from app.services.supabase import SupabaseClient

async def fetch_metrics():
    async with SupabaseClient().client() as c:
        r = await c.get("/calllog", params={"select": "*"})
        r.raise_for_status()
        data = r.json()

    total_calls = len(data)

    def get(d, *path, default=None):
        cur = d
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                return default
        return cur

    arrivals    = sum(1 for d in data if get(d, "structured_payload", "driver_status") == "Arrived")
    delays      = sum(1 for d in data if get(d, "structured_payload", "driver_status") == "Delayed")
    emergencies = sum(1 for d in data if get(d, "structured_payload", "scenario") == "Emergency")

    delay_sum = 0
    for d in data:
        v = get(d, "structured_payload", "delay_minutes", default=0) or 0
        try:
            delay_sum += int(v)
        except Exception:
            pass
    avg_delay = round(delay_sum / (delays or 1), 2)

    return {
        "total_calls": total_calls,
        "arrivals": arrivals,
        "delays": delays,
        "emergencies": emergencies,
        "avg_delay_minutes": avg_delay,
    }
