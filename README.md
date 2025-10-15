# AI Dispatch Voice Agent — Full Stack (FastAPI × Retell AI × Supabase × React)

A production-ready reference app that creates **AI dispatch voice calls** (web + phone), runs a **custom LLM** over Retell’s real-time WS protocol, **persists transcripts & structured insights** into Supabase, and provides a **React dashboard** for metrics, search, and CSV export.

This README explains the architecture, folder structure, how the code is modularized and scalable, how to run it locally (with ngrok), how Retell and Supabase are wired, what environment variables to set, and what features/bonus items are implemented.

---

## Highlights

- **Custom LLM Agent (Retell)** via WebSocket:
  - Endpoint: `wss://<backend>/api/v1/retell/llm-webhook/{call_id}`
  - Slot-filling dialog policy that avoids loops and ends gracefully.
- **Call lifecycle**:
  - Frontend triggers a **web call** → Backend calls Retell `/v2/create-web-call` → Frontend joins with Retell Web SDK.
- **Webhooks**:
  - Endpoint: `POST https://<backend>/api/v1/retell/webhook`
  - Handles `call_started`, `call_ended`, `call_analyzed`, stores transcript + structured payload.
- **Supabase persistence**:
  - Tables: `agent`, `driver`, `calllog`.
  - Auto-ensures FKs (agent/driver) to keep demo friction-free.
- **React Dashboard**:
  - **Metrics**: totals, delays, emergencies, average delay.
  - **Conversations**: full searchable table, filters, pagination, **CSV export**.
  - **Call Trigger**: start web calls from the browser and join in-app.
- **Scalability**:
  - Clean separation of **routers, services, repositories**.
  - Retell integration isolated, easy to extract into its own microservice.
  - Idempotent webhook upsert logic.

---

## Monorepo Layout

```
/backend
  app/
    api/v1/routers/
      calls.py               # POST /api/v1/calls/start (web/phone) → Retell create call
      llm_webhook.py         # WS handler for Custom LLM protocol (dialog policy)
      retell_webhook.py      # POST handler for Retell account/agent webhooks
      results.py             # GET /api/v1/results (raw call logs)
      metrics.py             # GET /api/v1/metrics (aggregates)
      conversations.py       # GET /api/v1/conversations (filters, paging), export.csv
      agents_supabase.py     # Helpers for agent CRUD over Supabase REST (optional)
      dev_diag.py            # Debug/diagnostics (optional)
    services/
      supabase.py            # Minimal REST client for Supabase (service key)
      agents_repo.py         # Ensure/fetch agent IDs (works with agent/agents table)
      drivers_repo.py        # Ensure/fetch driver IDs (auto-insert 'Unknown' if needed)
      postprocess.py         # Summarizes transcript → structured payload (ETA, delay, etc.)
    core/
      config.py              # Settings loader for .env
    main.py                  # FastAPI app, CORS, routers, healthz
  .env.example               # Backend envs (see below)
  requirements.txt

/frontend
  src/
    assets/components/Layout/
      Layout.tsx
      Sidebar.tsx            # Sidebar with routes (Dashboard, Agent Config, Call Trigger, Analytics, Conversations)
    assets/components/CallTrigger/
      CallTrigger.tsx        # Form to start a web call
      WebCallPanel.tsx       # Retell Web SDK (join/leave; events)
    assets/pages/
      HomePage.tsx
      DashboardPage.tsx      # Pulls /metrics
      AgentConfigPage.tsx
      CallTriggerPage.tsx
      AnalyticsPage.tsx
      ConversationsPage.tsx  # Pulls /conversations; CSV export
    services/api.ts          # All frontend API calls (with ngrok header workaround)
    AppRoutes.tsx            # React Router
  .env.example               # Frontend envs (see below)
  package.json
  vite.config.ts
```

### Why this structure scales

- **Routers** (HTTP/WS) are thin and declarative → easy to move into separate services (e.g., `voice-service`, `webhook-service`, `reporting-service`).
- **Service layer** (`services/*`) encapsulates external systems (Supabase REST, Retell policy/postprocess) → keeps boundaries clean.
- **Repositories** (`agents_repo.py`, `drivers_repo.py`) abstract persistence quirks (table name singular/plural), ensure IDs, and hide FK headaches.
- **Idempotent webhook upserts** guarantee consistent storage even if Retell retries.
- **Frontend** isolates screens/pages + API client → convenient to rebrand or embed.

---

## Backend Endpoints

## Supabase: Why REST over SDK

This project uses **Supabase’s direct REST API (PostgREST)** via `httpx` instead of the official SDK.

**Why we chose REST**
- **Stability in server-to-server flows:** Using the service role key in the `Authorization` header avoids local/ephemeral **SDK session refresh & token expiry** issues that can appear during development or when processes restart frequently.
- **Explicit control & debuggability:** We control headers like `Prefer: return=representation, count=exact` and query params (`select`, `order`, `ilike`, `eq`, etc.) directly, making responses predictable and easy to log and test (e.g., 200/201/204 paths).
- **Smaller dependency surface:** A single lightweight HTTP client (`httpx`) keeps the stack lean and predictable in containers and serverless.

**Security**
- The **service key is used only on the backend**. The frontend never receives any Supabase credentials.
- **Row Level Security** continues to apply; PostgREST enforces the same policies as the SDK.

**Easy to swap later**
- The calls are centralized in `app/services/supabase.py`. If you prefer the SDK later, replace that layer with SDK calls—no changes to routers or business logic needed.


### Calls
- `POST /api/v1/calls/start`  
  Creates a Retell call.
  - Body (web):
    ```json
    { "driver_name": "Alice", "load_number": "LDN-123", "call_type": "web" }
    ```
  - Returns:
    ```json
    {
      "provider_call_id": "retell_...",
      "retell": { "call_id": "call_...", "access_token": "..." }
    }
    ```
  - Frontend passes `access_token` to Retell Web SDK.

- (Optional) Phone call mode:
  ```json
  {
    "driver_name":"Alice",
    "driver_phone":"+15551234567",
    "from_number":"+15557654321",
    "load_number":"LDN-123",
    "call_type":"phone"
  }
  ```

### Retell Custom LLM (WS)
- `GET /api/v1/retell/llm-webhook/{call_id}` (Upgraded to WebSocket by Retell)
  - Sends initial greeting.
  - For each user turn, runs slot-filling policy:
    - Captures **location, ETA, delay reason** (if delayed).
    - If arrived/unloading, asks for door/lumper and POD reminder.
    - Handles noise/uncooperative/emergency cases.
    - Ends with a clear **confirmation & wrap**.
  - Keeps ephemeral **call state** server-side.

### Webhooks (HTTP)
- `POST /api/v1/retell/webhook`
  - Verifies signature (optional in dev).
  - Handles `call_started` (light touch), `call_ended` (final transcript), `call_analyzed`.
  - Extracts transcript and populates `structured_payload` via `postprocess.py`.
  - Upserts into `calllog` by `provider_call_id` or `retell_call_id`.
  - Ensures FKs for `agent` and `driver`.

### Reporting / Data
- `GET /api/v1/metrics`
  - `{ total_calls, arrivals, delays, emergencies, avg_delay_minutes }`
- `GET /api/v1/results?load_number=...`
  - Raw `calllog` rows.
- `GET /api/v1/conversations?q=&driver_name=&load_number=&status=&date_from=&date_to=&page=&limit=`
  - Returns `{ items, page, limit, total }` with joined driver view.
- `GET /api/v1/conversations/export.csv?...`
  - CSV of filtered conversations.

---

## Data Model (Supabase)

> You can adapt names (`agent` vs `agents`) — repos detect table name and columns.

**agent**
- `id` (PK, int)
- `name` (text, optional)
- `retell_agent_id` (text, optional)
- `created_at` (timestamptz, default `now()`)

**driver**
- `id` (PK, int)
- `name` (text, not null)
- `phone_number` (text, null allowed for web calls)
- `created_at` (timestamptz, default `now()`)

**calllog**
- `id` (PK, int)
- `agent_id` (FK → agent.id, not null)
- `driver_id` (FK → driver.id, not null)
- `load_number` (text, null ok)
- `provider_call_id` (text, unique-ish)
- `retell_call_id` (text)
- `status` (text: `initiated` | `updated` | `ended`)
- `scenario` (text: `Dispatch` | `Emergency` | etc.)
- `transcript` (text)
- `structured_payload` (jsonb)  
  e.g.
  ```json
  {
    "driver_status": "Delayed",
    "current_location": "I-80 Chicago",
    "eta": "in 15 minutes",
    "delay_reason": "Traffic",
    "unloading_status": "N/A",
    "call_outcome": "In-Transit Update",
    "pod_reminder_acknowledged": "false"
  }
  ```
- `call_start_time` (timestamptz, default `now()`)
- `call_end_time` (timestamptz, null until end)
- `created_at` (timestamptz, default `now()`)
- `conflicts` (jsonb, default `{}`)

> **RLS:** for demos, use the **service key**; in production, enable RLS and create policies for least-privileged access.

---

## Environment Variables

### Backend (`/backend/.env`)
```env
ENV=dev
API_PREFIX=/api

# CORS
cors_origins=http://localhost:5173

# Supabase (REST)
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOi...

# Retell
RETELL_API_KEY=key_xxx
RETELL_AGENT_ID=agent_xxx
RETELL_AGENT_VERSION=1
RETELL_BASE_URL=https://api.retellai.com
RETELL_WEBHOOK_SECRET=            # optional in dev; set in Retell dashboard too

# (Optional) Legacy DB URL (not used when Supabase REST is used)
DATABASE_URL=postgresql+psycopg://...
JWT_SECRET=dev-secret
```

### Frontend (`/frontend/.env`)
```env
VITE_API_BASE=http://127.0.0.1:8000        # or your ngrok https URL
VITE_RETELL_SDK_URL=https://cdn.retellai.com/web-sdk.js
VITE_RETELL_CONSTRUCTOR=RetellWebClient
```

> The frontend **adds** `ngrok-skip-browser-warning: true` on API calls to avoid HTML intercepts.

---

## Install & Run

### 1) Supabase: create tables

Execute SQL (adjust names if needed):

```sql
create table if not exists public.agent (
  id bigserial primary key,
  name text,
  retell_agent_id text,
  created_at timestamptz default now()
);

create table if not exists public.driver (
  id bigserial primary key,
  name text not null,
  phone_number text,
  created_at timestamptz default now()
);

create table if not exists public.calllog (
  id bigserial primary key,
  agent_id bigint not null references public.agent(id) on delete restrict,
  driver_id bigint not null references public.driver(id) on delete restrict,
  load_number text,
  provider_call_id text,
  retell_call_id text,
  status text,
  scenario text,
  transcript text,
  structured_payload jsonb default '{}'::jsonb,
  call_start_time timestamptz default now(),
  call_end_time timestamptz,
  created_at timestamptz default now(),
  conflicts jsonb default '{}'::jsonb
);
```

(Dev only) disable RLS or use service key with PostgREST. For prod, enable RLS and add policies.

### 2) Backend

```bash
cd backend
python -m venv .venv
. .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # and fill in values
uvicorn app.main:app --reload
# → http://127.0.0.1:8000/healthz
```

### 3) Frontend

```bash
cd frontend
npm i
cp .env.example .env   # set VITE_API_BASE to backend URL (local or ngrok)
npm run dev
# → http://localhost:5173
```

### 4) Ngrok (to expose backend to Retell)

```bash
ngrok http 8000
# Copy the https URL, e.g. https://your-subdomain.ngrok-free.app
```

### 5) Retell Agent (Dashboard)

- Create **Agent** → choose **Custom LLM**.
- **LLM Webhook URL** (WS):  
  `wss://<your-ngrok-domain>/api/v1/retell/llm-webhook/{call_id}`
- **Agent-level Webhook URL** (HTTP):  
  `https://<your-ngrok-domain>/api/v1/retell/webhook`
- (Optional) Set **Webhook Secret**, then set the same in backend `RETELL_WEBHOOK_SECRET`.
- Keep default TTS/ASR or configure to your preference.

---

## How a Call Flows

1. In the frontend **Call Trigger** page, submit Driver Name & Load #.
2. Frontend hits `POST /api/v1/calls/start`.
3. Backend posts to Retell `/v2/create-web-call`, returns `{ call_id, access_token }`.
4. Frontend instantiates `RetellWebClient` and calls `startCall({ accessToken })`.
5. Retell connects to our **LLM WS** endpoint → dialog policy runs.
6. When call ends, Retell posts **webhook** (`call_ended`) to our backend with transcript & metadata.
7. Backend summarizes → stores **transcript** and **structured_payload** in `calllog`.
8. **Dashboard** pulls `/api/v1/metrics`.  
   **Conversations** pulls `/api/v1/conversations` and can export CSV.

---

## Implementation Details

### Modularization & Interfaces

- **Routers** only orchestrate: parse inputs, call service/repo functions, return responses.
- **Services** implement external integrations:
  - `supabase.py` is a minimal typed client around PostgREST (headers, base URL).
  - `postprocess.py` extracts ETA/location/delay/unloading with simple regex; easy to swap with LLM call later.
- **Repositories**:
  - `agents_repo.py` & `drivers_repo.py` normalize schema differences (table name singular/plural), ensure IDs, and hide FK headaches.
- **Retell Web SDK** (`WebCallPanel.tsx`) listens to event hooks (joined, started, errors) and starts/stops calls safely.

### Scalability / Microservices

- Move `llm_webhook.py` (WS) to a `voice-service`.
- Move `retell_webhook.py` (HTTP) to a `webhooks-service`.
- Keep `conversations.py` and `metrics.py` under a `reporting-service`.
- They only share Supabase and an event schema (webhooks) → cleanly separable.

### Optimizations

- **Idempotent** upsert on webhook using both `provider_call_id` and `retell_call_id`.
- **Single-ask** slot filling (don’t loop the same question).
- **Ngrok HTML guard** in frontend to avoid “Unexpected token `<`”.
- **Auto-create** `agent` & `driver` rows to pass FK constraints with minimal setup friction.

---

## Frontend Screens

- **Dashboard** (`/dashboard`):
  - Cards: total calls, arrivals, delays, emergencies, avg delay.
  - Recent activity block (example).
- **Agent Config** (`/agent-config`):
  - Placeholder for agent settings UI (you can surface dynamic variables/templates here).
- **Call Trigger** (`/call-trigger`):
  - Form for driver name + load # → **Create Web Call**.
  - Panel to **Join Call**, shows connection state and errors.
- **Analytics** (`/analytics`):
  - Placeholder for charts or deeper KPIs using `/metrics`.
- **Conversations** (`/conversations`):
  - Filters: free text, driver name, load #, status, date range.
  - Pagination.
  - **Export CSV**.

---

## API Usage (Examples)

### Create Web Call

```bash
curl -X POST "$API_BASE/api/v1/calls/start" \
  -H "Content-Type: application/json" \
  -d '{"driver_name":"Alice","load_number":"LDN-123","call_type":"web"}'
```

### List Conversations

```bash
curl "$API_BASE/api/v1/conversations?q=traffic&status=Delayed&page=1&limit=20"
```

### Export CSV

```bash
curl -L "$API_BASE/api/v1/conversations/export.csv?status=Arrived&limit=1000" -o conversations.csv
```

### Metrics

```bash
curl "$API_BASE/api/v1/metrics"
```

---

## Troubleshooting

- **Stuck on “Joining”**  
  Ensure you pass **`accessToken`** to `RetellWebClient.startCall`. Some SDK versions don’t require `callId`. Check browser mic permissions.

- **401 Unauthorized on webhook**  
  You set `RETELL_WEBHOOK_SECRET` in backend but not in Retell dashboard (or vice versa). Align them (or leave empty for local dev).

- **403 on LLM WebSocket**  
  Make sure Retell connects to `wss://<ngrok-domain>/api/v1/retell/llm-webhook/{call_id}` and your server is publicly reachable.

- **Supabase FK or NOT NULL errors**  
  We auto-ensure `agent`/`driver`. If you changed constraints (e.g., `driver.phone_number` not null), either seed drivers or relax constraint for web calls.

- **Frontend fetch returns HTML (`<!DOCTYPE ...`)**  
  ngrok banner page. The API client already sends `ngrok-skip-browser-warning: true`. Double-check `VITE_API_BASE` and restart `npm run dev`.

- **No transcript in row**  
  Transcript arrives on `call_ended` (and/or `call_analyzed`). Confirm your agent-level webhook URL is correct and reachable. Check backend logs for `↪️  PATCH /calllog ... 200`.

---

## Security & Production Hardening

- Set **`RETELL_WEBHOOK_SECRET`** and verify signatures (already coded).
- Restrict **CORS** to your domain and add a simple **Bearer auth** for `/calls/start`.
- Turn on **RLS** in Supabase and create minimal access policies for your service role.
- Add **rate limiting**, **structured logs**, and redact sensitive data.
- Rotate **API keys** and keep **service key** off the client side.

---

## What’s Implemented vs Requirements

**Core requirements**
- Custom LLM agent over WS ✅
- Create & join web calls from UI ✅
- Dynamic variables passed ✅
- Webhooks capture transcript & details ✅
- Persist to Supabase with clean schema ✅
- Review data via APIs & UI ✅

**Bonus**
- Metrics API + dashboard ✅
- Conversations table with filters & CSV export ✅
- Auto-ensure agent/driver to smooth FKs ✅
- Ngrok guard and error-resilient flows ✅

**Easy next wins (optional)**
- Transcript view modal per row.
- Recording URL capture (time-limited) if Retell provides it → “Play recording”.
- Escalation flags (SLA breach detection).
- Multi-language greeting based on selected language in Call Trigger.

---

## Scripts / Commands Cheat Sheet

```bash
# Backend
uvicorn app.main:app --reload

# Frontend
npm run dev

# Ngrok
ngrok http 8000
```

---

## License

Internal demo reference; adapt licensing to your needs.
