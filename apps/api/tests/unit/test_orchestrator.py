"""Unit tests for the agent orchestrator (fully mocked, DB-free).

Verifies: authentication, intent routing, tool planning + execution,
agent run + tool call logging, evidence-grounded response, draft actions.
"""
from __future__ import annotations

import pytest

from app.schemas import AgentAnalyzeResponse
from app.services import orchestrator
from app.services.orchestrator import AgentAuthError

USER = {"id": "user-1", "email": "demo@finpilot.in", "display_name": "Demo", "currency": "INR"}


def fake_tool_executor(tool_name, user_id, args):
    if tool_name == "get_category_breakdown":
        return {"categories": [{"category": "Rent", "amount": 15000, "transaction_count": 1}],
                "total_expenses": 15000, "start_date": "2026-06-01"}
    if tool_name == "get_monthly_summary":
        return {"has_data": True, "year": 2026, "month": 6, "period_label": "Jun 2026",
                "income": 65000, "expenses": 15000, "net": 50000, "savings_rate": 76.9,
                "committed": 15649, "category_breakdown": [], "largest_expenses": [],
                "month_over_month": {}, "insights": [], "transactions_analyzed": 2}
    if tool_name == "detect_anomalies":
        return {"period": "2026-06", "anomalies": [
            {"type": "category_spike", "category": "Food", "actual": 4800, "baseline": 3000,
             "difference": 1800, "percentage": 60.0, "threshold": "x",
             "explanation": "Food spending is 60% higher than the previous 3-month average of",
             "references": ["t1"]}], "count": 1, "has_data": True}
    if tool_name == "calculate_committed_budget":
        return {"year": 2026, "month": 6, "has_data": True, "income": 65000,
                "committed": 15649, "spent": 15000, "available": 49351,
                "discretionary": 34351, "monthly_savings": 50000,
                "assumptions": ["Committed = active recurring payments expressed per month."]}
    if tool_name == "get_financial_goals":
        return {"goals": [{"id": "g1", "name": "Emergency fund", "target_amount": 200000,
                           "current_amount": 75000, "remaining": 125000, "progress_pct": 37.5,
                           "target_date": "2028-09-01", "priority": 1,
                           "required_monthly": 5208.33}], "count": 1}
    if tool_name == "simulate_expense_change":
        return {"monthly_savings": 50000, "projected_monthly_savings": 40000,
                "goal_impact": {"goal": "Emergency fund", "months_baseline": 3,
                                "months_scenario": 4, "delay_months": 1, "impact": "delayed"}}
    if tool_name in ("get_recurring_payments", "get_upcoming_obligations",
                     "get_transactions", "simulate_goal", "compare_periods"):
        return {"payments": [], "count": 0}
    return {}


@pytest.fixture(autouse=True)
def mock_all(monkeypatch):
    monkeypatch.setattr("app.db.get_user_by_id", lambda uid: USER if uid == "user-1" else None)
    monkeypatch.setattr("app.db.create_agent_run",
                        lambda uid, q, intent=None: "run-abc")
    monkeypatch.setattr("app.db.create_agent_tool_call",
                        lambda run_id, tool, args: f"call-{tool}")
    calls = []

    def complete_tool(call_id, output, status="completed", started_at=None):
        calls.append(("tool", call_id, status))

    def complete_run(run_id, status="completed", final_response=None, started_at=None):
        calls.append(("run", run_id, status))

    monkeypatch.setattr("app.db.complete_agent_tool_call", complete_tool)
    monkeypatch.setattr("app.db.complete_agent_run", complete_run)
    monkeypatch.setattr("app.db.create_action_draft",
                        lambda uid, atype, title, description="", payload=None: f"draft-{title[:4]}")
    monkeypatch.setattr("app.services.orchestrator.tools.execute_tool", fake_tool_executor)


def test_unknown_user_rejected(mock_all):
    with pytest.raises(AgentAuthError):
        orchestrator.run_agent("nobody", "Where did I spend the most?")


def test_agent_run_returns_grounded_response(mock_all):
    resp = orchestrator.run_agent("user-1", "Where did I spend the most this month?")
    assert isinstance(resp, AgentAnalyzeResponse)
    assert resp.run_id == "run-abc"
    assert resp.intent == "spend_most"
    assert "rent" in resp.answer.lower()
    assert resp.evidence, "evidence must be present"
    assert resp.calculations, "calculations must be present"
    assert resp.assumptions is not None
    assert resp.latency_ms >= 0


def test_agent_run_builds_activity_trail(mock_all):
    resp = orchestrator.run_agent("user-1", "What changed this month?")
    steps = [s.step for s in resp.activity]
    assert "Intent detected" in steps
    assert "Tool executed" in steps
    assert "Response generated" in steps
    tools_called = [s.tool for s in resp.activity if s.tool]
    assert "compare_periods" in tools_called and "get_monthly_summary" in tools_called


def test_agent_run_creates_draft_actions_from_findings(mock_all):
    resp = orchestrator.run_agent("user-1", "Why is my food bill so high?")
    titles = [a.title for a in resp.recommended_actions]
    assert any("Food" in t for t in titles), titles
    assert any(a.id.startswith("draft-") for a in resp.recommended_actions)