"""Subscription Guardian router - Phase 7.

Read-only detection plus explicit, idempotent draft creation.
Anything that would change the user's money (cancel, contact, execute)
is deliberately absent: approvals flow through /api/actions/{id}/approve.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app import db
from app.services import guardian

router = APIRouter(tags=["guardian"])


class GuardianDraftRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    merchant: str = Field(..., min_length=1)


@router.get("/guardian/detect")
def detect(user_id: str = Query(..., min_length=1)):
    """Subscription signals for a user (read-only, never executes anything)."""
    if db.get_user_by_id(user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    return guardian.detect(user_id)


@router.get("/guardian/summary")
def summary(user_id: str = Query(..., min_length=1)):
    """Compact dashboard summary of guardian activity (read-only)."""
    if db.get_user_by_id(user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    return guardian.summarize(user_id)


@router.post("/guardian/draft")
def create_draft(req: GuardianDraftRequest):
    """Create a review DRAFT for one flagged merchant (idempotent)."""
    if db.get_user_by_id(req.user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        return guardian.create_draft(req.user_id, req.merchant)
    except guardian.GuardianError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc