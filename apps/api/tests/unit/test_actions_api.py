"""API-level unit tests for action drafts (DB mocked)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

USER = {"id": "user-1", "email": "demo@finpilot.in", "display_name": "Demo", "currency": "INR"}

ACTIONS = [
    {"id": "a-1", "action_type": "review", "title": "Review Netflix subscription",
     "description": "Subscription looks recurring-like.", "status": "draft",
     "approved_at": None, "executed_at": None,
     "payload_json": {}, "created_at": "2026-09-19T00:00:00Z"},
    {"id": "a-2", "action_type": "review", "title": "Already approved",
     "status": "approved", "approved_at": "2026-09-19T00:00:00Z",
     "executed_at": None, "payload_json": {}, "created_at": "2026-09-19T00:00:00Z"},
]


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    monkeypatch.setattr("app.db.get_user_by_id", lambda uid: USER if uid == "user-1" else None)
    monkeypatch.setattr("app.db.list_action_drafts",
                        lambda uid, status=None, limit=50:
                            [a for a in ACTIONS if (status is None or a["status"] == status)])
    monkeypatch.setattr("app.db.get_action_draft",
                        lambda aid: next((a for a in ACTIONS if a["id"] == aid), None))
    monkeypatch.setattr("app.db.update_action_status",
                        lambda aid, status: None)


def test_list_actions_drafts(mock_db):
    r = client.get("/api/actions", params={"user_id": "user-1", "status": "draft"})
    assert r.status_code == 200
    assert r.json()["count"] == 1


def test_approve_draft(mock_db):
    r = client.post("/api/actions/a-1/approve")
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


def test_approve_non_draft_conflicts(mock_db):
    r = client.post("/api/actions/a-2/approve")
    assert r.status_code == 409


def test_reject_draft(mock_db):
    r = client.post("/api/actions/a-1/reject")
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_approve_missing_action_404(mock_db):
    r = client.post("/api/actions/missing/approve")
    assert r.status_code == 404