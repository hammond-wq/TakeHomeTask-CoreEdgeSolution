from __future__ import annotations
import re
from typing import Any, Dict, List

TIME_RE = re.compile(r"\b(?:at\s*)?(\d{1,2}:\d{2}\s*(?:am|pm)?)\b|\b(?:in\s*)?(\d+)\s*(?:min|mins|minutes|hr|hrs|hours)\b", re.I)
CITY_HWY_RE = re.compile(r"\b(?:i-\d{1,3}|us-\d{1,3}|hwy\s*\d+|highway\s*\d+|[A-Z][a-z]+(?:,\s*[A-Z]{2})?)\b")
REASON_RE = re.compile(r"\b(traffic|weather|accident|construction|breakdown|tire|blowout|police|road\s*closure|detour)\b", re.I)
UNLOAD_RE = re.compile(r"\b(door\s*\d+|in\s*door|waiting\s*for\s*lumper|lumper|detention|unloading|checked\s*in)\b", re.I)

def extract_eta(text: str) -> str | None:
    m = TIME_RE.search(text or "")
    return m.group(0) if m else None

def extract_location(text: str) -> str | None:
    m = CITY_HWY_RE.search(text or "")
    return m.group(0) if m else None

def extract_delay_reason(text: str) -> str | None:
    m = REASON_RE.search(text or "")
    return m.group(1).title() if m else None

def extract_unloading(text: str) -> str | None:
    m = UNLOAD_RE.search(text or "")
    if not m: return None
    val = m.group(0).strip().title()
    return "In Door" if val.lower().startswith("in door") else val

def classify_status(text: str) -> str:
    t = (text or "").lower()
    if any(k in t for k in ["arrived","checked in","docked","at dock","in door"]): return "Arrived"
    if any(k in t for k in ["unloading","lumper","detention","in door"]):          return "Unloading"
    if any(k in t for k in ["delay","late","behind","traffic","weather","stuck"]): return "Delayed"
    return "Driving"

def detect_emergency(text: str) -> str | None:
    t = (text or "").lower()
    if any(k in t for k in ["accident","crash","collision"]): return "Accident"
    if any(k in t for k in ["blowout","breakdown","flat","engine"]): return "Breakdown"
    if any(k in t for k in ["medical","injur","bleeding","faint"]):  return "Medical"
    return None

def is_noisy(text: str) -> bool:
    return len((text or "").strip()) < 3 or "??" in (text or "")

def is_uncoop(text: str) -> bool:
    return (text or "").strip().lower() in {"yes","no","ok","k","fine","later"}

def latest_user(transcript: list) -> str:
    if not isinstance(transcript, list): return ""
    for utt in reversed(transcript):
        if isinstance(utt, dict) and (utt.get("role") or "").lower() == "user":
            return (utt.get("content") or "").strip()
    return ""

def text_from_transcript_object(obj: Any) -> str:
    if not isinstance(obj, list):
        return ""
    lines: List[str] = []
    for u in obj:
        if not isinstance(u, dict):
            continue
        role = (u.get("role") or "").strip().lower()
        content = (u.get("content") or "").strip()
        if not content:
            continue
        who = "Driver" if role == "user" else "Agent"
        lines.append(f"{who}: {content}")
    return "\n".join(lines)

def pluck_transcript(call_obj: Dict[str, Any]) -> str:
    if not isinstance(call_obj, dict):
        return ""
    t = call_obj.get("transcript") or call_obj.get("transcript_text")
    if isinstance(t, str) and t.strip():
        return t.strip()
    obj = call_obj.get("transcript_object") or call_obj.get("transcript_with_tool_calls")
    s = text_from_transcript_object(obj)
    return s.strip()
