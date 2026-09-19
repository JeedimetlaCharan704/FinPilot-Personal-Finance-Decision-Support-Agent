"""Health router — Phase 2 substrate behavior, preserved exactly."""
from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {"status": "ok", "service": settings.service_name}