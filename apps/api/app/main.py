"""FinPilot API entrypoint.

Endpoints:
  GET /api/health      -> {"status": "ok", "service": "finpilot-api"}
  GET /api/db/health   -> DB connectivity descriptor (Phase 3). Never leaks secrets.

CORS is environment-based. No wildcard "*" in production (see config.py).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import db_health, health

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="FinPilot decision-support backend. Your bank app tells you what you spent; FinPilot tells you what you can do.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(db_health.router, prefix="/api")


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"service": settings.service_name, "message": "FinPilot backend. See /docs for the API reference."}