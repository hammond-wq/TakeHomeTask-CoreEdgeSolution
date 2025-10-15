# app/api/v1/routers/retell_webhook.py
from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
import hmac, hashlib, json, datetime as dt

from app.core.config import settings
from app.services.supabase import SupabaseClient
from app.services.postprocess import summarize_transcript
from app.services.agents_repo import AgentsRepo
from app.services.drivers_repo import DriversRepo

router = APIRouter(prefix="/api/v1/retell", tags=["retell"])


# ---------- helpers ----------

def _verify_signature(headers, body: bytes) -> bool:
    # Dev-friendly: allow empty secret (e.g. when testing via ngrok)
    secret = (settings.retell_webhook_secret or "").encode()
    if not secret:
        return True
    sig = headers.get("retell-signature") or headers.get("x-retell-signature")
    if not sig:
        return False
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


async def _patch_calllog(where: dict, patch: dict) -> bool:
    async with SupabaseClient().client() as c:
        params = {}
        if "provider_call_id" in where and where["provider_call_id"]:
            params["provider_call_id"] = f"eq.{where['provider_call_id']}"
        if "retell_call_id" in where and where["retell_call_id"]:
            params["retell_call_id"] = f"eq.{where['retell_call_id']}"
        if not params:
            return False

        r = await c.patch("/calllog", params=params, json=patch)
        try:
            data = r.json()
        except Exception:
            data = r.text
        print("↪️  PATCH /calllog", r.status_code, data)
        return r.status_code < 400


async def _post_calllog(row: dict):
    async with SupabaseClient().client() as c:
        r = await c.post("/calllog", json=row)
        try:
            data = r.json()
        except Exception:
            data = r.text
        print("↪️  POST /calllog", r.status_code, data)
        return r


def _pluck_transcript(payload: dict) -> str:
    """
    Retell may send:
      - transcript_text: str
      - transcript: list of {role, content}
      - post_call_analysis.transcript: str
    """
    t = (
        payload.get("transcript_text")
        or payload.get("transcript")
        or (payload.get("post_call_analysis") or {}).get("transcript")
        or ""
    )
    if isinstance(t, list):
        # Join user + assistant content if array form
        try:
            parts = []
            for u in t:
                if isinstance(u, dict) and u.get("content"):
                    parts.append(u["content"])
            return " ".join(parts)
        except Exception:
            return ""
    return t or ""


# ---------- webhook ----------

@router.post("/webhook")
async def retell_webhook(request: Request):
    raw = await request.body()
    if not _verify_signature(request.headers, raw):
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        # accept and stop retries on non-JSON
        return {"ok": True}

    # 0) Retell "challenge" handshake (future-proof)
    if isinstance(payload, dict) and "challenge" in payload:
        return {"challenge": payload["challenge"]}

    # 1) Identify the call
    retell_call_id = (
        payload.get("call_id")
        or payload.get("id")
        or (payload.get("call") or {}).get("id")
    )
    meta = payload.get("metadata") or {}
    provider_call_id = meta.get("provider_call_id") or payload.get("provider_call_id")
    load_number = meta.get("load_number") or payload.get("load_number")

    # 2) Driver hints (from dynamic variables/metadata)
    dyn = payload.get("retell_llm_dynamic_variables") or {}
    driver_name = dyn.get("driver_name") or meta.get("driver_name")
    driver_phone = dyn.get("driver_phone") or meta.get("driver_phone")

    # 3) Transcript + summary
    transcript = _pluck_transcript(payload)
    summary = summarize_transcript(transcript or "")
    scenario = "Emergency" if summary.get("call_outcome") == "Emergency Escalation" else "Dispatch"

    # 4) Ensure foreign keys (will create if empty tables)
    agent_db_id = (await AgentsRepo.ensure_agent_id()) or 1
    driver_db_id = (await DriversRepo.ensure_driver_id(driver_name, driver_phone)) or 1

    # 5) Build patch/update
    patch = {
        "retell_call_id": retell_call_id,
        "load_number": load_number,
        "structured_payload": summary,        # jsonb
        "transcript": transcript or None,     # text
        "scenario": scenario,
        "status": "ended" if transcript else "updated",
        "call_end_time": dt.datetime.utcnow().isoformat() + "Z" if transcript else None,
        "agent_id": agent_db_id,
        "driver_id": driver_db_id,
    }
    patch = {k: v for k, v in patch.items() if v is not None}

    # 6) Try update by provider_call_id, then retell_call_id; otherwise create
    updated = False
    if provider_call_id:
        updated = await _patch_calllog({"provider_call_id": provider_call_id}, patch)
    if not updated and retell_call_id:
        updated = await _patch_calllog({"retell_call_id": retell_call_id}, patch)

    if not updated:
        base = {
            "provider_call_id": provider_call_id,
            "retell_call_id": retell_call_id,
            **patch,
        }
        await _post_calllog(base)

    return {"ok": True}
