# app/services/postprocess.py
from __future__ import annotations
import re
from typing import Dict, Any

EMERGENCY_KEYWORDS = [
    "emergency", "accident", "blowout", "crash", "medical", "pulling over", "pulled over"
]

def _has_emergency(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in EMERGENCY_KEYWORDS)

def _extract_location(text: str) -> str | None:
    # naive location hints (highways, mile markers, cities)
    mm = re.search(r"(i[-\s]?\d+\s*(north|south|east|west)?(?:,\s*mile\s*marker\s*\d+)?)", text, re.I)
    if mm: return mm.group(0)
    city = re.search(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b(?:,\s*[A-Z]{2})?", text)
    return city.group(0) if city else None

def _extract_eta(text: str) -> str | None:
    m = re.search(r"(eta|arriv(e|al))[^\.:\n]*?((\d{1,2}[:.]\d{2}\s*(am|pm))|tomorrow|today|in\s+\d+\s*(min|mins|minutes|hours|hrs))", text, re.I)
    return m.group(0) if m else None

def _extract_unloading(text: str) -> str | None:
    for k in ["unloading", "door", "lumper", "detention", "waiting"]:
        if k in text.lower(): return k.title()
    return None

def _extract_delay(text: str) -> str | None:
    t = text.lower()
    if "traffic" in t: return "Heavy Traffic"
    if "weather" in t or "snow" in t or "rain" in t: return "Weather"
    if "breakdown" in t: return "Mechanical"
    return "None"

def _extract_status(text: str) -> str:
    t = text.lower()
    if "arrived" in t: return "Arrived"
    if "unloading" in t or "in door" in t or "dock" in t: return "Unloading"
    if "delay" in t or "late" in t: return "Delayed"
    return "Driving"

def _extract_pod_ack(text: str) -> bool:
    t = text.lower()
    return "pod" in t and any(k in t for k in ["email", "send", "text", "will", "share", "upload"])

def _extract_emergency_fields(text: str) -> Dict[str, Any]:
    t = text.lower()
    if "blowout" in t or "flat" in t: etype = "Breakdown"
    elif "accident" in t or "crash" in t or "collision" in t: etype = "Accident"
    elif "medical" in t or "injur" in t: etype = "Medical"
    else: etype = "Other"
    safety = "Driver confirmed everyone is safe" if "safe" in t else "Unknown"
    injury = "No injuries reported" if "no injur" in t or "nobody hurt" in t else ("Injuries reported" if "injur" in t or "hurt" in t else "Unknown")
    loc = _extract_location(text) or "Unknown"
    load_secure = "secure" in t or "strapped" in t
    return {
        "emergency_type": etype,
        "safety_status": safety,
        "injury_status": injury,
        "emergency_location": loc,
        "load_secure": load_secure,
        "escalation_status": "Connected to Human Dispatcher",
    }

def summarize_transcript(transcript: str) -> Dict[str, Any]:
    """
    Returns a dict matching the doc's required fields for:
      - Scenario 1 (check-in)
      - Scenario 2 (emergency escalation)
    """
    if _has_emergency(transcript):
        fields = {"call_outcome": "Emergency Escalation"}
        fields.update(_extract_emergency_fields(transcript))
        return fields

    # Scenario 1 – End-to-end check-in
    status = _extract_status(transcript)
    outcome = "Arrival Confirmation" if status in ("Arrived", "Unloading") else "In-Transit Update"
    return {
        "call_outcome": outcome,
        "driver_status": status,                  # Driving / Delayed / Arrived / Unloading
        "current_location": _extract_location(transcript) or "Unknown",
        "eta": _extract_eta(transcript) or "Unknown",
        "delay_reason": _extract_delay(transcript),
        "unloading_status": _extract_unloading(transcript) or ("N/A" if status not in ("Arrived","Unloading") else "Unknown"),
        "pod_reminder_acknowledged": _extract_pod_ack(transcript),
    }
