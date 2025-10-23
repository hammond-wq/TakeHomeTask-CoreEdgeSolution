# AI Dispatch Voice Agent — Full Stack (FastAPI × Retell AI × Pipecat × Supabase × React)

A production-ready reference app that creates **AI dispatch voice calls** (web + phone), runs a **custom LLM** over Retell’s real-time WS protocol and **Pipecat runtime**, persists **transcripts + structured insights** into Supabase, and provides a **React dashboard** for metrics, analytics, search, and CSV export.

This README documents both **Part 1 (Retell AI)** and **Part 2 (Pipecat & Analytics)**—explaining how the codebase was extended in a modular, injectable, and scalable way.

---

## 🚀 Highlights

### 🧩 Dual-Engine Voice AI
- **Custom LLM Agent (Retell)** via WebSocket  
  `wss://<backend>/api/v1/retell/llm-webhook/{call_id}`
- **Self-hosted Pipecat runtime** for on-prem voice agents  
  `POST /api/v1/voice/start?vendor=pipecat`
- **Unified Analytics Layer** — both Retell and Pipecat metrics are visualized together.

### 🔄 Call Lifecycle
1. Frontend triggers a call (Retell or Pipecat).  
2. Backend orchestrates the provider, returning an access token or session.  
3. Voice session runs → structured metrics logged to Supabase.  
4. Webhook/Observer sends session summary (`duration`, interruptions, keywords, sentiment).  
5. React dashboard visualizes KPIs in real time.

### 🧱 Architecture Additions (Part 2)
- `/api/v1/pipecat/metrics` and `/api/v1/pipecat/event` endpoints.
- Analytics UI (`AnalyticsPage.tsx`) with Retell + Pipecat tabs, cards, and Recharts.
- Observer loop in Pipecat bot (`bot.py`) posting `session_summary` events.
- Supabase schema extended with calllog metrics columns (duration, interruptions, keyword_hits).

---

## 🗂 Monorepo Layout

```
/backend
  app/
    api/v1/routers/
      calls.py                # POST /api/v1/calls/start → Retell or Pipecat call
      llm_webhook.py          # WS: Retell custom LLM policy
      retell_webhook.py       # HTTP webhook for Retell events
      pipecat_events.py       # NEW: POST /pipecat/event & GET /pipecat/metrics
      metrics.py              # Retell metrics summary
      conversations.py        # Conversation search + CSV export
    services/
      supabase.py             # REST client for Supabase (PostgREST)
      analytics_repo.py       # NEW: aggregates Retell & Pipecat metrics
      agents_repo.py          # Ensures agent FK
      drivers_repo.py         # Ensures driver FK
    core/
      config.py               # .env loader + CORS
    main.py                   # FastAPI bootstrap + router mount
  requirements.txt
  .env.example

/frontend
  src/
    assets/pages/
      DashboardPage.tsx
      AnalyticsPage.tsx       # NEW: dual Retell / Pipecat charts + cards
      ConversationsPage.tsx
      CallTriggerPage.tsx
    services/api.ts
    assets/components/Layout/
      Layout.tsx | Sidebar.tsx
  vite.config.ts
  package.json
```

---

## 🧮 Why This Scales (Even After Part 2)

| Layer | Responsibility | Scalability Benefit |
|:--|:--|:--|
| **Routers** | Thin HTTP/WS entrypoints | Can split into microservices (`voice-service`, `reporting-service`) |
| **Services Layer** | External integrations (Supabase, Retell, Pipecat) | Swap vendor APIs without breaking logic |
| **Repositories** | Persistence helpers (FK guarantee, table name auto-detect) | Portable between DBs (Postgres, Supabase) |
| **Observers / Events** | Pipecat runtime telemetry loop → backend | Decoupled analytics event bus |
| **Frontend pages** | Independent feature modules | Plug-and-play screens for future vendors |

Every part of Part 2 was added **non-destructively** — no legacy code overwritten; all new modules are imported and mounted cleanly.

---

## 🧠 New Backend Endpoints (Part 2)

### POST `/api/v1/pipecat/event`
Receives structured runtime events from Pipecat bot (summarized session data).

**Body**
```json
{
  "provider_call_id": "abc123",
  "event_type": "session_summary",
  "data": {
    "duration_secs": 60,
    "keywords": ["traffic","emergency"],
    "interruptions": 1,
    "sentiment": 0.92
  }
}
```

### GET `/api/v1/pipecat/metrics`
Returns aggregated metrics for all Pipecat calls:
```json
{
  "items": [
    {
      "id": 145,
      "driver_id": 40,
      "load_number": "7891-B",
      "created_at": "2025-10-20T17:29:50Z",
      "duration_secs": 36.6,
      "interruptions_est": 0,
      "tokens_estimated": 0,
      "keyword_hits": {}
    }
  ]
}
```

---

## 📊 Frontend — Analytics Page (Part 2)

- **Dual View:** toggle between Retell and Pipecat metrics.  
- **Stat Cards:** totals, averages, emergencies, delays, etc.  
- **Charts:** Bar + Pie (Recharts) with responsive containers.  
- **Error-safe fetch:** defensive JSON handling so no crash on API error.  

**File:** `src/assets/pages/AnalyticsPage.tsx`  
Now fully wired to backend APIs:
- `GET /api/v1/metrics` → Retell cards & charts  
- `GET /api/v1/pipecat/metrics` → Pipecat charts (duration, keyword distribution)

---

## 🧮 Supabase Schema Extensions

Added columns to `calllog` to support Pipecat analytics:
```sql
alter table calllog
add column if not exists duration_secs numeric default 0,
add column if not exists interruptions_est integer default 0,
add column if not exists tokens_estimated integer default 0,
add column if not exists keyword_hits jsonb default '{}'::jsonb;
```

---

## ⚙️ Environment Variables (Extended)

### Backend (`.env`)
```env
# Pipecat
PIPECAT_BASE_URL=http://127.0.0.1:8000
PIPECAT_API_KEY=pipecat_local_key
```

### Frontend (`.env`)
```env
VITE_API_BASE=http://127.0.0.1:8000
```

---

## 🧠 Pipecat Runtime Integration (bot.py)

```python
async def send_event(evt_type, data):
    async with httpx.AsyncClient(timeout=10.0) as rc:
        await rc.post(f"{BACKEND_BASE}/api/v1/pipecat/event", json={
            "provider_call_id": PROVIDER_ID,
            "event_type": evt_type,
            "data": data,
        })

await send_event("session_summary", {
    "duration_secs": duration_secs,
    "keywords": keywords,
    "interruptions": interruptions,
    "sentiment": sentiment_score
})
```

This runs as part of the session loop and sends metrics back to FastAPI.

---

## 🧩 Modularity and Injectability Enhancements (Part 2)

- **Event Handler Injection:** `/pipecat/event` is vendor-agnostic—supports future voice providers without refactor.  
- **Analytics Repository:** centralizes metrics fetch, making both Retell and Pipecat pluggable data sources.  
- **Frontend Abstraction:** `AnalyticsPage.tsx` chooses provider via `view state`; no hardcoded URLs.  
- **Type-safe state management:** unified parsing and mapping avoids runtime crashes.  

Each layer (Pipecat, Retell, Analytics) can be disabled or swapped out independently — true injectable design.

---

## ✅ Progress Summary

| Feature | Status |
|:--|:--:|
| Retell LLM WS flow | ✅ |
| Pipecat voice runtime | ✅ |
| Event bridge (`/pipecat/event`) | ✅ |
| Metrics API (`/pipecat/metrics`) | ✅ |
| Unified Analytics Dashboard | ✅ |
| Supabase persistence | ✅ |
| Structured reporting + charts | ✅ |

---

## 🏁 Conclusion

This monorepo is now a **dual-engine AI dispatch platform**, modular enough to host multiple voice vendors (Retell, Pipecat, and beyond).  
Backend and frontend are fully decoupled and scalable, ready for production deployment or extension into microservices.
