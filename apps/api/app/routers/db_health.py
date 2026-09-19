"""DB health router — Phase 3.

GET /api/db/health -> 200 when connected:
    {"status": "ok", "service": "finpilot-api", "database": "connected"}
Returns 503 with a NON-SECRET descriptor when not configured/unreachable.
"""
from __future__ import annotations

from fastapi import APIRouter, Response

from app import db
from app.config import get_settings

router = APIRouter(tags=["health", "db"])


@router.get("/db/health")
def db_health() -> dict:
    settings = get_settings()
    info = db.check_db_health()

    if info["status"] == "connected":
        return {"status": "ok", "service": settings.service_name, "database": "connected"}

    # Not configured / unreachable -> clear, non-secret error state.
    response = {"status": "error", "service": settings.service_name, "database": info["status"]}
    message = info.get("message")
    if message:
        response["message"] = message
    # Signal via status code for faster triage by the frontend health badge.
    # Using JSONResponse to set 503 without returning a raw Exception.
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=503, content=response)