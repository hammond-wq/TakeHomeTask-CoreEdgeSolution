from __future__ import annotations
from app.core.config import settings
from app.vendors.base import VoiceVendor
from app.vendors.pipecat_vendor import PipecatVendor
from app.vendors.retell_vendor import RetellVendor

def get_vendor(name: str | None = None) -> VoiceVendor:
    vendor = (name or settings.voice_vendor or "retell").lower()
    if vendor == "pipecat":
        return PipecatVendor()
    if vendor == "retell":
        return RetellVendor()
    raise ValueError(f"Unknown vendor: {vendor}")
