"""API-level unit tests for the simulation endpoints (DB mocked)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

USER = {"id": "user-1", "email": "demo@finpilot.in", "display_name": "Demo", "currency": "INR"}

RESULT = {
    "baseline": {"label": "projection", "monthly_income": 65000, "monthly_expenses": 20000,
                 "monthly_savings": 45000, "savings_rate": 69.2, "committed": 15649},
    "scenario": {"label": "Laptop", "monthly_income": 65000, "monthly_expenses": 20000,
                 "monthly_savings": 45000, "savings_rate": 69.2, "committed": 15649},
    "difference": {"monthly_savings": 0, "annualized": 0, "one_time": 60000, "total_cumulative": 60000},
    "goal_impact": {"goal": "Emergency fund", "months_baseline": 3, "months_scenario": 5,
                    "delay_months": 2, "impact": "delayed"},
    "explanation": "Baseline (Jun 2026): you save about 45000 per month.",
    "assumptions": ["No real transactions are changed; this is a hypothetical scenario."],
}


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    monkeypatch.setattr("app.db.get_user_by_id", lambda uid: USER if uid == "user-1" else None)
    monkeypatch.setattr("app.db.create_simulation", lambda *a, **k: "sim-1")
    monkeypatch.setattr("app.db.list_simulations",
                        lambda uid, limit=50: [{"id": "sim-1", "purchase_name": "Laptop",
                                                "purchase_amount": 60000}])
    monkeypatch.setattr("app.routers.simulations.simulations.run_simulation",
                        lambda *a, **k: dict(RESULT))


def test_run_purchase_simulation(mock_db):
    r = client.post("/api/simulations", json={
        "user_id": "user-1", "scenario_type": "purchase", "name": "Laptop",
        "amount": 60000, "frequency": "one_time", "duration_months": 1,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["simulation_id"] == "sim-1"
    assert body["goal_impact"]["delay_months"] == 2
    assert body["difference"]["one_time"] == 60000
    assert body["baseline"]["monthly_savings"] == 45000


def test_run_simulation_requires_amount(mock_db):
    r = client.post("/api/simulations", json={
        "user_id": "user-1", "scenario_type": "purchase", "name": "Laptop",
        "amount": 0, "frequency": "one_time",
    })
    assert r.status_code == 422


def test_run_simulation_unknown_user(mock_db):
    r = client.post("/api/simulations", json={
        "user_id": "nobody", "scenario_type": "purchase", "name": "Laptop",
        "amount": 1000, "frequency": "one_time",
    })
    assert r.status_code == 404


def test_list_simulations(mock_db):
    r = client.get("/api/simulations", params={"user_id": "user-1"})
    assert r.status_code == 200
    assert r.json()["simulations"][0]["id"] == "sim-1"