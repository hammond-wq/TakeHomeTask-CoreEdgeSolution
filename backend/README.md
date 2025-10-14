# AI Call Agent — FastAPI Backend (Skeleton)

Clean/Hexagonal structure for enterprise scalability.

## Run
1. Copy `.env.example` to `.env` and edit values.
2. `uvicorn app.main:app --reload --port 8000`
3. Open http://localhost:8000/docs

# TABLE DB CREATION QUERIES
create table if not exists public.agent (
  id bigserial primary key,
  name text not null,
  language text not null,
  voice_type text not null,
  active boolean not null default true,
  created_at timestamptz not null default now()
);
create index if not exists ix_agent_name on public.agent (name);



