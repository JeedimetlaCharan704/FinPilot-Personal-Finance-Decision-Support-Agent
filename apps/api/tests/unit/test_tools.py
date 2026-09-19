"""Unit tests for the internal tool system (services mocked, DB-free)."""
from __future__ import annotations

import pytest

from app.services import tools
from app.services.tools import ToolValidationError


def test_known_tools_registered():
    expected = {"get_transactions", "get_monthly_summary", "get_category_breakdown",
                "get_recurring_payments", "get_financial_goals", "get_budget_status",
                "compare_periods", "detect_anomalies", "simulate_goal",
                "simulate_expense_change", "calculate_committed_budget",
                "get_upcoming_obligations"}
    assert expected <= set(tools.TOOLS)


def test_unknown_tool_rejected():
    with pytest.raises(ToolValidationError):
        tools.validate_tool("does_not_exist", {})


def test_missing_required_argument_rejected():
    with pytest.raises(ToolValidationError):
        tools.validate_tool("simulate_expense_change", {})  # needs amount


def test_execute_category_breakdown(monkeypatch):
    fake = lambda user_id, start_date=None, end_date=None, year=None, month=None: {
        "categories": [{"category": "Food", "amount": 4800, "transaction_count": 12}],
        "total_expenses": 4800,
    }
    monkeypatch.setattr("app.services.tools.analytics.category_breakdown", fake)
    out = tools.execute_tool("get_category_breakdown", "user-1", {})
    assert out["categories"][0]["category"] == "Food"
    assert out["total_expenses"] == 4800


def test_tool_output_shapes(monkeypatch):
    calls = {}

    def fake_summary(user_id, year=None, month=None):
        calls["summary"] = True
        return {"has_data": True, "income": 1, "expenses": 2, "net": -1,
                "savings_rate": 0, "committed": 0, "category_breakdown": [],
                "largest_expenses": [], "month_over_month": {}, "insights": []}

    monkeypatch.setattr("app.services.tools.analytics.monthly_summary", fake_summary)
    out = tools.execute_tool("get_monthly_summary", "user-1", {})
    assert out["net"] == -1
    assert calls["summary"] is True