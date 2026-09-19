"""API-level unit tests for agent endpoints (DB fully mocked)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

USER = {"id": "user-1", "email": "demo@finpilot.in", "display_name": "Demo", "currency": "INR"}

RUNS = [
    {"id": "run-1", "question": "Where did I spend the most?",
     "status": "completed", "started_at": "2026-09-19T00:00:00Z",
     "completed_at": "2026-09-19T00:00:01Z", "final_response": '{"answer": "x"}',
     "created_at": "2026-09-19T00:00:00Z"},
]

TOOL_CALLS = [
    {"id": "call-1", "tool_name": "get_category_breakdown", "status": "completed",
     "input_json": {}, "output_json": {"categories": []},
     "started_at": "2026-09-19T00:00:00Z", "completed_at": "2026-09-19T00:00:01Z"},
]


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    monkeypatch.setattr("app.db.get_user_by_id", lambda uid: USER if uid == "user-1" else None)
    monkeypatch.setattr("app.db.list_agent_runs",
                        lambda uid, limit=50: RUNS)
    monkeypatch.setattr("app.db.get_agent_run", lambda run_id: RUNS[0] if run_id == "run-1" else None)
    monkeypatch.setattr("app.db.list_agent_tool_calls", lambda run_id: TOOL_CALLS)


def test_analyze_rejects_unknown_user(mock_db):
    r = client.post("/api/agent/analyze",
                    json={"user_id": "nobody", "question": "Where did I spend the most?"})
    assert r.status_code == 404


def test_list_runs(mock_db):
    r = client.get("/api/agent/runs", params={"user_id": "user-1"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["runs"][0]["id"] == "run-1"
    assert "user_id" not in body["runs"][0]


def test_run_detail_with_tool_calls(mock_db):
    r = client.get("/api/agent/runs/run-1")
    assert r.status_code == 200
    body = r.json()
    assert body["run"]["id"] == "run-1"
    assert body["tool_calls"][0]["tool_name"] == "get_category_breakdown"


def test_run_detail_404(mock_db):
    r = client.get("/api/agent/runs/missing")
    assert r.status_code == 404