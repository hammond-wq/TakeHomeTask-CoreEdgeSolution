# app/services/supabase.py
from __future__ import annotations
import os, httpx

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_KEY")

def supa_headers():
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

class SupabaseClient:
    def __init__(self):
        self._base = f"{SUPABASE_URL}/rest/v1"

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base, headers=supa_headers())
