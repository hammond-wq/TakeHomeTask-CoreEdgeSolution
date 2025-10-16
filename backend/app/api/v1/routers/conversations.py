from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException
from starlette.responses import StreamingResponse, JSONResponse
from typing import Optional, List, Tuple
import csv, io, datetime as dt
from app.services.supabase import SupabaseClient

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])

def _iso_start(s: Optional[str]) -> Optional[str]:
    """YYYY-MM-DD -> start of day Z; ISO -> normalized Z."""
    if not s:
        return None
    try:
        if len(s) == 10:
            return dt.datetime.fromisoformat(s).replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "Z"
        return dt.datetime.fromisoformat(s.replace("Z", "")).isoformat() + "Z"
    except Exception:
        return None

def _iso_end(s: Optional[str]) -> Optional[str]:
    """YYYY-MM-DD -> end of day Z; ISO -> normalized Z."""
    if not s:
        return None
    try:
        if len(s) == 10:
            return dt.datetime.fromisoformat(s).replace(hour=23, minute=59, second=59, microsecond=999000).isoformat() + "Z"
        return dt.datetime.fromisoformat(s.replace("Z", "")).isoformat() + "Z"
    except Exception:
        return None

async def _fetch_conversations(
    q: Optional[str],
    driver_name: Optional[str],
    load_number: Optional[str],
    status: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    page: int,
    limit: int,
):
    page = max(1, page)
    limit = max(1, min(200, limit))
    offset = (page - 1) * limit

    
    driver_select = "driver:driver_id(name,phone_number)"
    join_driver_inner = bool(driver_name)
    if join_driver_inner:
        driver_select = "driver!inner(name,phone_number)"

    
    params: List[Tuple[str, str]] = [
        ("select", f"id,created_at,load_number,status,scenario,transcript,structured_payload,{driver_select}"),
        ("order", "created_at.desc"),
        ("limit", str(limit)),
        ("offset", str(offset)),
    ]

    if q:
        params.append(("transcript", f"ilike.*{q}*"))
    if driver_name:
        params.append(("driver.name", f"ilike.*{driver_name}*"))
    if load_number:
        params.append(("load_number", f"eq.{load_number}"))
    if status:
        params.append(("structured_payload->>driver_status", f"eq.{status}"))

    since = _iso_start(date_from)
    until = _iso_end(date_to)
    if since:
        params.append(("created_at", f"gte.{since}"))
    if until:
        params.append(("created_at", f"lte.{until}"))

    
    async with SupabaseClient().client() as c:
        r = await c.get(
            "/calllog",
            params=params,
            headers={"Prefer": "return=representation, count=exact"},
        )
        if r.status_code >= 400:
            raise HTTPException(r.status_code, r.text)

        data = r.json()
        
        total = None
        cr = r.headers.get("content-range") or ""
        if "/" in cr:
            try:
                total = int(cr.split("/")[-1])
            except Exception:
                total = None

        return data, (total or len(data))

@router.get("/")  
async def list_conversations(
    q: str | None = Query(None),
    driver_name: str | None = Query(None),
    load_number: str | None = Query(None),
    status: str | None = Query(None, description="Driver status in structured_payload: Driving|Delayed|Arrived|Unloading"),
    date_from: str | None = Query(None, description="YYYY-MM-DD or ISO"),
    date_to: str | None = Query(None, description="YYYY-MM-DD or ISO"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
):
    items, total = await _fetch_conversations(q, driver_name, load_number, status, date_from, date_to, page, limit)
    return JSONResponse({"items": items, "page": page, "limit": limit, "total": total})

@router.get("/export.csv")
async def export_conversations_csv(
    q: str | None = Query(None),
    driver_name: str | None = Query(None),
    load_number: str | None = Query(None),
    status: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    limit: int = Query(2000, ge=1, le=10000),
):
    items, _ = await _fetch_conversations(q, driver_name, load_number, status, date_from, date_to, 1, limit)

    def row(d):
        drv = (d.get("driver") or {}) if isinstance(d.get("driver"), dict) else {}
        sp = d.get("structured_payload") or {}
        return [
            d.get("id"),
            d.get("created_at"),
            drv.get("name") or "",
            drv.get("phone_number") or "",
            d.get("load_number") or "",
            sp.get("driver_status") or "",
            d.get("scenario") or "",
            (d.get("transcript") or "").replace("\n", " ").strip()[:500],
        ]

    sio = io.StringIO()
    w = csv.writer(sio)
    w.writerow(["id", "created_at", "driver_name", "driver_phone", "load_number", "driver_status", "scenario", "transcript_snippet"])
    for d in items:
        w.writerow(row(d))
    sio.seek(0)

    return StreamingResponse(
        sio,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="conversations.csv"'},
    )
