from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.routers.calls import router as calls_router
from app.api.v1.routers.retell_webhook import router as retell_router
from app.api.v1.routers.llm_webhook import router as llm_router
from app.api.v1.routers.results import router as results_router
from app.api.v1.routers.agents_supabase import router as agents_router
from app.api.v1.routers.dev_diag import router as dev_router




app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")] if settings.cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(calls_router)
app.include_router(retell_router)
app.include_router(llm_router)
app.include_router(results_router)
app.include_router(agents_router)
app.include_router(dev_router)

@app.get("/healthz")
def healthz():
    return {"ok": True}
