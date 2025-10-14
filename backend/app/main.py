# app/main.py
from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os, json

app = FastAPI(title="AI Voice Agent API", version="1.0.0")

# CORS
origins = []
try:
    origins = json.loads(os.getenv("CORS_ORIGINS", "[]"))
except Exception:
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
from app.api.v1.routers.agents_supabase import router as agents_router
from app.api.v1.routers.calls import router as calls_router
from app.api.v1.routers.retell_webhook import router as retell_router
from app.api.v1.routers.results import router as results_router

app.include_router(agents_router)
app.include_router(calls_router)
app.include_router(retell_router)
app.include_router(results_router)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}
