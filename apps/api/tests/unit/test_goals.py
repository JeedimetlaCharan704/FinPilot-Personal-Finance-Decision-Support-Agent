"""Unit tests for goal intelligence (DB mocked)."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.services import goals

FUTURE = (date.today() + timedelta(days=730)).isoformat()  # ~24 months out

GOALS = [
    {"id": "g-emergency", "name": "Emergency fund", "target_amount": 200000,
     "current_amount": 75000, "target_date": FUTURE, "priority": 1,
     "status": "in_progress"},
    {"id": "g-laptop", "name": "New laptop", "target_amount": 60000,
     "current_amount": 0, "target_date": None, "priority": 2,
     "status": "in_progress"},
]


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    monkeypatch.setattr("app.db.fetch_goals", lambda user_id: GOALS)


def test_goal_analysis_progress(mock_db):
    ga = goals.goal_analysis("user-1")
    assert ga["count"] == 2
    emergency = ga["goals"][0]
    assert emergency["remaining"] == 125000
    assert round(emergency["progress_pct"], 1) == 37.5
    assert emergency["required_monthly"] is not None


def test_primary_goal_is_highest_priority(mock_db):
    g = goals.primary_goal("user-1")
    assert g["name"] == "Emergency fund"


def test_goal_impact_purchase_delay(mock_db):
    gi = goals.goal_impact("user-1", monthly_savings=10000, one_time=60000)
    assert gi["goal"] == "Emergency fund"
    assert gi["months_baseline"] == 13      # ceil(125000 / 10000)
    assert gi["months_scenario"] == 19      # ceil(185000 / 10000)
    assert gi["delay_months"] == 6
    assert gi["impact"] == "delayed"


def test_goal_impact_extra_savings_accelerates(mock_db):
    gi = goals.goal_impact("user-1", monthly_savings=10000, delta_monthly=2000)
    assert gi["months_baseline"] == 13
    assert gi["months_scenario"] == 11      # ceil(125000 / 12000)
    assert gi["delay_months"] == -2
    assert gi["impact"] == "accelerated"