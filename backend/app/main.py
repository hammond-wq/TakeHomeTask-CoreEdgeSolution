# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings, setup_logging
from app.api.v1.routers.calls import router as calls_router
from app.api.v1.routers.retell_webhook import router as retell_router
from app.api.v1.routers.llm_webhook import router as llm_router
from app.api.v1.routers.results import router as results_router
from app.api.v1.routers.agents_supabase import router as agents_router
from app.api.v1.routers.dev_diag import router as dev_router
from app.api.v1.routers import metrics
from app.api.v1.routers import conversations

from app.middleware.error_handler import http_error_handler
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.request_timing import RequestTimingMiddleware

from app.api.v1.routers.pipecat_adapter import router as pipecat_router
from app.api.v1.routers.voice_start import router as voice_router
from app.api.v1.routers.pipecat_events import router as pipecat_events_router
from app.api.v1.routers.analytics_pipecat import router as analytics_pipecat

from app.api.v1.routers.pipecat_metrics import router as pipecat_metrics




setup_logging()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")] if settings.cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RequestTimingMiddleware)

app.include_router(calls_router)
app.include_router(retell_router)
app.include_router(llm_router)
app.include_router(results_router)
app.include_router(agents_router)
app.include_router(dev_router)
app.include_router(metrics.router)
app.include_router(conversations.router)
app.include_router(pipecat_router)
app.include_router(voice_router)
app.include_router(pipecat_events_router)
app.include_router(analytics_pipecat)
app.include_router(pipecat_metrics)

@app.exception_handler(StarletteHTTPException)
async def _http_exc_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(RequestValidationError)
async def _validation_exc_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

@app.exception_handler(Exception)
async def _unhandled_exc_handler(request: Request, exc: Exception):
    return await http_error_handler(request, exc)

@app.get("/healthz")
def healthz():
    return {"ok": True}
