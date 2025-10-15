# app/services/postprocess.py
import re

def summarize_transcript(text: str) -> dict:
    t = (text or "").lower()

    # detect emergency first
    if any(k in t for k in ["accident","crash","collision","blowout","breakdown","medical"]):
        return {
            "call_outcome": "Emergency Escalation",
            "emergency_type": ("Accident" if "accident" in t or "crash" in t else
                               "Breakdown" if "blowout" in t or "breakdown" in t else
                               "Medical" if "medical" in t else "Other"),
            "safety_status": "Driver confirmed safe" if "i'm safe" in t or "i am safe" in t else "Unknown",
            "injury_status": "No injuries reported" if "no injur" in t else "Unknown",
            "emergency_location": _first(r"(i-\d+|us-\d+|mile\s*marker\s*\d+|[A-Z][a-z]+,\s*[A-Z]{2})", t),
            "load_secure": "true" if "load secure" in t else "false" if "load not secure" in t else "unknown",
            "escalation_status": "Connected to Human Dispatcher",
        }

    status = ("Unloading" if "unloading" in t or "lumper" in t or "detention" in t else
              "Arrived" if "arrived" in t or "checked in" in t or "in door" in t else
              "Delayed" if "delay" in t or "late" in t else "Driving")

    return {
        "call_outcome": "Arrival Confirmation" if status in ("Arrived","Unloading") else "In-Transit Update",
        "driver_status": status,
        "current_location": _first(r"(i-\d+|us-\d+|hwy\s*\d+|[A-Z][a-z]+,\s*[A-Z]{2})", t),
        "eta": _first(r"(\d{1,2}:\d{2}\s*(?:am|pm)?)|(\d+\s*(?:min|mins|minutes|hr|hrs|hours))", t),
        "delay_reason": _first(r"(traffic|weather|construction|breakdown|accident|police|detour)", t, title=True) or "None",
        "unloading_status": _first(r"(door\s*\d+|in\s*door|waiting\s*for\s*lumper|detention|unloading)", t, title=True) or "N/A",
        "pod_reminder_acknowledged": "true" if "pod" in t and ("ok" in t or "will do" in t) else "false",
    }

def _first(pattern: str, text: str, title: bool=False):
    m = re.search(pattern, text, re.I)
    if not m: return None
    s = m.group(0)
    return s.title() if title else s
