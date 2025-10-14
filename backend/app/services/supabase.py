from __future__ import annotations
import httpx

# Hardcoded values (replace these with actual values)
SUPABASE_URL = "https://tdqfcycljpezeygmoxch.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRkcWZjeWNsanBlemV5Z21veGNoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA0NDUzNzcsImV4cCI6MjA3NjAyMTM3N30.2zJPoU-TTt_ft_EFUfeqvJ_QY1bNoo_bxMzCqgGQuDk"

# Check if the variables are set correctly
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
