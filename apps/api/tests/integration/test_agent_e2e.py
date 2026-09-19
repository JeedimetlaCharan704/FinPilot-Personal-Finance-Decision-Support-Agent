"""Phase 4 integration tests - live Supabase (skipped when not configured).

Exercises the real agent pipeline: analyze -> tools -> logging -> simulations
-> analytics. Reads demo user from the live database (no hardcoded secrets).
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

from fastapi.testclient import TestClient

from app.main import app
from app import db

client = TestClient(app)


@pytest.fixture(autouse=True)
def disable_llm(monkeypatch):
    """Integration tests must NEVER make paid LLM calls.

    They validate the deterministic pipeline against the live Supabase
    project; the LLM path is covered by mocked unit tests and the single
    manual smoke test in Phase 5.
    """
    monkeypatch.setattr("app.services.orchestrator.get_provider", lambda: None)
    yield


QUESTIONS = [
    "Where did I spend the most this month?",
    "What changed compared with last month?",
    "How much am I committed to?",
    "Am I on track for my emergency fund?",
    "Can I afford a 60000 rupee laptop?",
]


def _uid() -> str:
    user = db.get_demo_user()
    assert user is not None, "seeded demo user must exist"
    return user["id"]


def test_analyze_intent_and_evidence():
    uid = _uid()
    r = client.post("/api/agent/analyze",
                    json={"user_id": uid, "question": QUESTIONS[0]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["intent"] == "spend_most"
    assert body["answer"]
    assert body["evidence"], "evidence must be grounded in data"
    assert body["run_id"]
    assert any(s["step"] == "Intent detected" for s in body["activity"])


def test_analyze_all_question_types():
    uid = _uid()
    for q in QUESTIONS:
        r = client.post("/api/agent/analyze", json={"user_id": uid, "question": q})
        assert r.status_code == 200, f"{q}: {r.text[:300]}"
        assert r.json()["answer"], f"empty answer for {q}"


def test_agent_run_is_persisted_and_traceable():
    uid = _uid()
    r = client.post("/api/agent/analyze",
                    json={"user_id": uid, "question": "Which recurring payments are coming up?"})
    run_id = r.json()["run_id"]
    detail = client.get(f"/api/agent/runs/{run_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["run"]["status"] == "completed"
    assert any(t["tool_name"] == "get_upcoming_obligations"
               for t in body["tool_calls"])


def test_simulation_persisted():
    uid = _uid()
    r = client.post("/api/simulations", json={
        "user_id": uid, "scenario_type": "purchase", "name": "Laptop",
        "amount": 60000, "frequency": "one_time", "duration_months": 1,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["baseline"]["monthly_income"] > 0
    assert "goal" in body["goal_impact"]
    assert body["assumptions"]

    listing = client.get("/api/simulations", params={"user_id": uid})
    assert listing.status_code == 200
    assert listing.json()["count"] >= 1


def test_analytics_endpoints_hit_real_data():
    uid = _uid()
    for path in ("/api/analytics/monthly", "/api/analytics/categories",
                 "/api/analytics/recurring", "/api/analytics/goals"):
        r = client.get(path, params={"user_id": uid})
        assert r.status_code == 200, path
    m = client.get("/api/analytics/monthly", params={"user_id": uid}).json()
    assert m["has_data"] is True
    assert m["transactions_analyzed"] > 0


def test_action_draft_lifecycle():
    """Approve/reject a DRAFT action (never executes anything financial).

    The demo emergency fund is only ~38% funded, so the goal-track question
    deterministically produces a 'Contribute more to Emergency fund' draft.
    """
    uid = _uid()
    r = client.post("/api/agent/analyze",
                    json={"user_id": uid, "question": "Am I on track for my emergency fund?"})
    drafts = [a for a in r.json().get("recommended_actions", []) if a["id"]]
    assert drafts, "expected at least one draft action from goal analytics"
    action_id = drafts[0]["id"]
    appr = client.post(f"/api/actions/{action_id}/approve")
    assert appr.status_code == 200
    assert appr.json()["status"] == "approved"
    again = client.post(f"/api/actions/{action_id}/approve")
    assert again.status_code == 409  # not a draft anymore