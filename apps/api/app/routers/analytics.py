"""Analytics router - Phase 4 (deterministic, database-grounded)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app import db
from app.services import analytics, anomalies, goals

router = APIRouter(tags=["analytics"])


def _require_user(user_id: str) -> None:
    if db.get_user_by_id(user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")


@router.get("/analytics/monthly")
def monthly(user_id: str = Query(..., min_length=1),
            year: int | None = Query(None, ge=2020, le=2100),
            month: int | None = Query(None, ge=1, le=12)):
    _require_user(user_id)
    return analytics.monthly_summary(user_id, year, month)


@router.get("/analytics/categories")
def categories(user_id: str = Query(..., min_length=1),
               start_date: str | None = None,
               end_date: str | None = None):
    _require_user(user_id)
    return analytics.category_breakdown(user_id, start_date=start_date, end_date=end_date)


@router.get("/analytics/recurring")
def recurring(user_id: str = Query(..., min_length=1)):
    _require_user(user_id)
    return analytics.recurring_analysis(user_id)


@router.get("/analytics/goals")
def goals_endpoint(user_id: str = Query(..., min_length=1)):
    _require_user(user_id)
    return goals.goal_analysis(user_id)


@router.get("/analytics/anomalies")
def anomalies_endpoint(user_id: str = Query(..., min_length=1),
                       year: int | None = Query(None, ge=2020, le=2100),
                       month: int | None = Query(None, ge=1, le=12)):
    _require_user(user_id)
    return anomalies.detect_anomalies(user_id, year, month)


@router.get("/analytics/budget")
def budget(user_id: str = Query(..., min_length=1),
           year: int | None = Query(None, ge=2020, le=2100),
           month: int | None = Query(None, ge=1, le=12)):
    _require_user(user_id)
    return analytics.budget_status(user_id, year, month)