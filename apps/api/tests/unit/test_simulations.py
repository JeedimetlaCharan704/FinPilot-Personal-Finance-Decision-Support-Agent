"""Unit tests for the decision simulation engine (DB mocked)."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.services import simulations

FUTURE = (date.today() + timedelta(days=730)).isoformat()

BASELINE = {
    "has_data": True, "year": 2026, "month": 6, "period_label": "Jun 2026",
    "income": 65000, "expenses": 20000, "net": 45000, "savings_rate": 69.2,
    "committed": 15649, "category_breakdown": [], "largest_expenses": [],
    "month_over_month": {}, "insights": [], "transactions_analyzed": 4,
}

GOALS = [
    {"id": "g1", "name": "Emergency fund", "target_amount": 200000,
     "current_amount": 75000, "target_date": FUTURE, "priority": 1,
     "status": "in_progress"},
]

RECURRING = [
    {"id": "r-netflix", "merchant": "Netflix", "amount": 649,
     "frequency": "monthly", "next_payment_date": "2026-07-01", "status": "active"},
]


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    def fake_recurring(user_id, status="active"):
        return RECURRING if status == "active" else []

    monkeypatch.setattr("app.db.fetch_recurring", fake_recurring)
    monkeypatch.setattr("app.db.fetch_goals", lambda user_id: GOALS)


@pytest.fixture(autouse=True)
def mock_baseline(monkeypatch):
    monkeypatch.setattr("app.services.simulations.analytics.monthly_summary",
                        lambda user_id: dict(BASELINE))


def test_purchase_simulation(mock_db, mock_baseline):
    r = simulations.run_simulation("user-1", "purchase", "Laptop", 60000)
    assert r["baseline"]["monthly_savings"] == 45000
    assert r["scenario"]["monthly_savings"] == 45000  # one-time, not monthly
    assert r["difference"]["one_time"] == 60000
    gi = r["goal_impact"]
    assert gi["goal"] == "Emergency fund"
    assert gi["months_baseline"] == 3       # ceil(125000 / 45000)
    assert gi["months_scenario"] == 5       # ceil(185000 / 45000)
    assert gi["delay_months"] == 2
    assert "assumptions" in r and r["assumptions"]
    assert "informational analysis" in " ".join(r["assumptions"]).lower()


def test_rent_increase_simulation(mock_db, mock_baseline):
    # +INR 10,000/mo -> savings 35,000; ceil(125000/45000)=3 vs ceil(125000/35000)=4 -> delay 1
    r = simulations.run_simulation("user-1", "rent_increase", "", 10000,
                                   frequency="monthly", duration_months=12)
    assert r["scenario"]["monthly_savings"] == 35000
    assert r["difference"]["monthly_savings"] == -10000
    assert r["difference"]["annualized"] == -10000 * 12
    assert r["goal_impact"]["delay_months"] == 1


def test_extra_savings_simulation(mock_db, mock_baseline):
    # +INR 20,000/mo -> savings 65,000; ceil(125000/65000)=2 vs 3 -> accelerates by 1 month
    r = simulations.run_simulation("user-1", "extra_savings", "", 20000)
    assert r["scenario"]["monthly_savings"] == 65000
    assert r["goal_impact"]["delay_months"] == -1


def test_cancel_subscription_simulation(mock_db, mock_baseline):
    r = simulations.run_simulation("user-1", "cancel_subscription", "",
                                   0, reference_id="r-netflix")
    assert r["scenario"]["monthly_savings"] == 45649
    assert r["scenario"]["label"] == "Cancel Netflix"