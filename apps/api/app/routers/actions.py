"""Action drafts router - Phase 4.

AI creates DRAFT actions only. Approve/reject are explicit human decisions.
NEVER executes financial transactions.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app import db

router = APIRouter(tags=["actions"])


@router.get("/actions")
def list_actions(user_id: str = Query(..., min_length=1),
                 status: str | None = Query(None, pattern="^(draft|approved|rejected|executed)$"),
                 limit: int = Query(50, ge=1, le=200)):
    if db.get_user_by_id(user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    rows = db.list_action_drafts(user_id, status=status, limit=limit)
    for r in rows:
        r.pop("user_id", None)
    return {"actions": rows, "count": len(rows)}


@router.post("/actions/{action_id}/approve")
def approve(action_id: str):
    action = db.get_action_draft(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    if action["status"] != "draft":
        raise HTTPException(status_code=409,
                            detail=f"Action is already {action['status']}")
    db.update_action_status(action_id, "approved")
    return {"status": "approved", "action_id": action_id}


@router.post("/actions/{action_id}/reject")
def reject(action_id: str):
    action = db.get_action_draft(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    if action["status"] != "draft":
        raise HTTPException(status_code=409,
                            detail=f"Action is already {action['status']}")
    db.update_action_status(action_id, "rejected")
    return {"status": "rejected", "action_id": action_id}