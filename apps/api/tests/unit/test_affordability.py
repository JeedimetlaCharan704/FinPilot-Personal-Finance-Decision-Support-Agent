"""Phase 6 hero test suite: "Can I afford this?" decision flow.

Covers: INR parsing, safety limits, afford_purchase intent, deterministic
decision results (verdict/scenarios/goal impact), grounding (never invented
numbers), LLM-failure fallback, and the registered decision tool.
All tests are hermetic (no DB, no provider access).
"""
from __future__ import annotations

import re

import pytest

from app.llm.base import LLMError
from app.llm.validation import is_ungrounded
from app.services import intents, orchestrator, tools
from app.services.affordability import (
    MAX_PURCHASE_AMOUNT, evaluate_affordability, parse_purchase_amount,
    validate_purchase_amount,
)

USER = {"id": "user-1", "email": "demo@finpilot.in", "display_name": "Demo", "currency": "INR"}

SUMMARY = {
    "has_data": True, "year": 2026, "month": 6, "period_label": "Jun 2026",
    "income": 65000.0, "expenses": 39278.0, "net": 25722.0,
    "savings_rate": 39.6, "committed": 30649.0, "category_breakdown": [],
    "largest_expenses": [], "month_over_month": {}, "insights": [],
    "transactions_analyzed": 9,
}

BUDGET = {
    "has_data": True, "year": 2026, "month": 6, "income": 65000.0,
    "committed": 30649.0, "spent": 39278.0, "available": 34351.0,
    "discretionary": -4927.0, "monthly_savings": 25722.0, "assumptions": [],
}

GOALS = {
    "goals": [
        {"id": "g1", "name": "Emergency fund", "target_amount": 200000.0,
         "current_amount": 75000.0, "remaining": 125000.0, "progress_pct": 37.5,
         "target_date": "2027-03-31", "priority": 1, "status": "in_progress",
         "months_to_target": 6, "required_monthly": 20833.33},
        {"id": "g2", "name": "New laptop", "target_amount": 60000.0,
         "current_amount": 0.0, "remaining": 60000.0, "progress_pct": 0.0,
         "target_date": "2026-12-31", "priority": 3, "status": "in_progress",
         "months_to_target": 3, "required_monthly": 20000.0},
    ],
    "count": 2,
}


@pytest.fixture(autouse=True)
def mock_finance(monkeypatch):
    monkeypatch.setattr("app.services.analytics.monthly_summary",
                        lambda user_id, year=None, month=None: SUMMARY)
    monkeypatch.setattr("app.services.analytics.budget_status",
                        lambda user_id, year=None, month=None: BUDGET)
    monkeypatch.setattr("app.services.goals.goal_analysis",
                        lambda user_id: GOALS)
    monkeypatch.setattr("app.services.affordability.analytics.monthly_summary",
                        lambda user_id, year=None, month=None: SUMMARY)
    monkeypatch.setattr("app.services.affordability.analytics.budget_status",
                        lambda user_id, year=None, month=None: BUDGET)
    monkeypatch.setattr("app.services.affordability.goals.goal_analysis",
                        lambda user_id: GOALS)


# ---------------------------------------------------------------------------
# 1-4. Natural-language INR parsing + safety (STEP 4).
# ---------------------------------------------------------------------------
class TestParsePurchaseAmount:
    def test_rupee_comma_separated(self):
        assert parse_purchase_amount("Can I afford a \u20b965,000 laptop next month?") == 65000.0

    def test_rupee_plain_digits(self):
        assert parse_purchase_amount("Can I afford a \u20b965000 laptop?") == 65000.0

    def test_bare_comma_separated(self):
        assert parse_purchase_amount("Can I buy a 65,000 phone?") == 65000.0

    def test_bare_plain_digits(self):
        assert parse_purchase_amount("Can I buy a 50000 phone next month?") == 50000.0

    def test_k_suffix(self):
        assert parse_purchase_amount("Can I spend 65k on a trip?") == 65000.0
        assert parse_purchase_amount("Can I spend \u20b965k next month?") == 65000.0
        assert parse_purchase_amount("Can I spend \u20b920k on a trip next month?") == 20000.0

    def test_trailing_currency_word(self):
        assert parse_purchase_amount("Can I afford a 60,000 rupee laptop?") == 60000.0
        assert parse_purchase_amount("Can I afford a 65000 inr laptop?") == 65000.0

    def test_monitor_example(self):
        assert parse_purchase_amount("Can I afford a \u20b930,000 monitor?") == 30000.0

    def test_invalid_amounts_rejected(self):
        assert parse_purchase_amount("Can I afford a \u20b90 laptop?") is None
        assert parse_purchase_amount("Can I afford a -5000 phone?") is None
        assert parse_purchase_amount("Can I afford a \u20b92,000,000 laptop?") is None
        assert parse_purchase_amount("What changed compared with last month?") is None
        assert parse_purchase_amount("") is None
        assert parse_purchase_amount("Can I afford this laptop in 2026?") is None  # year only

    def test_validate_purchase_amount_limits(self):
        assert validate_purchase_amount(65000) == 65000.0
        assert validate_purchase_amount(1) == 1.0
        with pytest.raises(ValueError):
            validate_purchase_amount(0)
        with pytest.raises(ValueError):
            validate_purchase_amount(MAX_PURCHASE_AMOUNT + 1)
        with pytest.raises(ValueError):
            validate_purchase_amount("abc")


# ---------------------------------------------------------------------------
# 5. afford_purchase intent planning (STEP 2).
# ---------------------------------------------------------------------------
class TestIntent:
    def test_afford_purchase_intent_and_tool(self):
        info = intents.classify("Can I afford a \u20b965,000 laptop next month?")
        assert info["intent"] == "afford_purchase"
        assert "evaluate_affordability" in info["tools"]

    def test_intent_label(self):
        assert intents.intent_label("afford_purchase") == "affordability simulation"

    def test_decision_tool_registered(self):
        assert "evaluate_affordability" in tools.TOOLS
        with pytest.raises(tools.ToolValidationError):
            tools.execute_tool("evaluate_affordability", "user-1", {})


# ---------------------------------------------------------------------------
# 6-7. Deterministic decision result + goal impact (STEP 3/5/6).
# ---------------------------------------------------------------------------
class TestEvaluateAffordability:
    def test_not_yet_for_65000(self):
        out = evaluate_affordability("user-1", 65000)
        assert out["has_data"] is True
        assert out["verdict"] == "NOT_YET"
        assert out["purchase_amount"] == 65000.0
        assert out["projected_income"] == 65000.0
        assert out["committed_outflows"] == 30649.0
        assert out["normal_discretionary_spend"] == 8629.0  # 39278 - 30649
        assert out["free_cash"] == 25722.0
        assert out["cash_after_purchase"] == -39278.0
        assert out["months_to_save"] == 3  # ceil(65000 / 25722)

    def test_affordable_when_within_free_cash(self):
        out = evaluate_affordability("user-1", 20000)
        assert out["verdict"] == "AFFORDABLE"
        assert out["cash_after_purchase"] == 5722.0
        assert out["months_to_save"] == 1

    def test_tight_band(self):
        out = evaluate_affordability("user-1", 40000)  # 1x < 40000 <= 2x free cash
        assert out["verdict"] == "TIGHT"
        assert out["months_to_save"] == 2

    def test_goal_impacts_deterministic(self):
        out = evaluate_affordability("user-1", 65000)
        impacts = {g["goal"]: g for g in out["goal_impacts"]}
        ef = impacts["Emergency fund"]
        assert ef["months_baseline"] == 5          # ceil(125000 / 25722)
        assert ef["months_after_purchase"] == 8    # ceil(190000 / 25722)
        assert ef["delay_months"] == 3
        assert ef["impact"] == "delayed"
        assert ef["required_monthly_baseline"] == pytest.approx(20833.33, abs=0.01)
        assert ef["required_monthly_scenario"] == pytest.approx(31666.67, abs=0.01)
        lap = impacts["New laptop"]
        assert lap["months_baseline"] == 3         # ceil(60000 / 25722)
        assert lap["months_after_purchase"] == 5   # ceil(125000 / 25722)
        assert lap["delay_months"] == 2

    def test_scenarios_sourced_from_deterministic_numbers(self):
        out = evaluate_affordability("user-1", 65000)
        labels = [s["label"] for s in out["scenarios"]]
        assert labels[0] == "Buy now"
        by_label = {s["label"]: s for s in out["scenarios"]}
        buy_now = by_label["Buy now"]
        assert buy_now["cash_after_purchase"] == -39278.0
        assert buy_now["goal_delay_months"] == 3
        save = by_label["Save 3 months, then buy"]
        assert save["cash_after_purchase"] == 12166.0   # 3*25722 - 65000
        assert save["months_to_save"] == 3
        assert save["goal_delay_months"] == 0           # saving first removes the delay
        assert by_label["Trim discretionary spending"]["amount"] == 65000.0
        assert by_label["Trim discretionary spending"]["goal_delay_months"] == 0
        assert by_label["Smaller purchase"]["amount"] == 25722.0

    def test_no_data_verdict(self, monkeypatch):
        monkeypatch.setattr("app.services.affordability.analytics.monthly_summary",
                            lambda user_id, year=None, month=None:
                            {**SUMMARY, "has_data": False, "net": 0.0})
        out = evaluate_affordability("user-1", 65000)
        assert out["verdict"] == "INSUFFICIENT_DATA"

    def test_unsafe_amount_rejected(self):
        out = evaluate_affordability("user-1", MAX_PURCHASE_AMOUNT + 1)
        assert out["verdict"] == "INSUFFICIENT_DATA"
        assert out["warnings"]


# ---------------------------------------------------------------------------
# 8-10. Grounded response + LLM failure fallback (no invented numbers).
# ---------------------------------------------------------------------------
DECISION = {
    "has_data": True, "verdict": "NOT_YET", "purchase_amount": 65000.0,
    "projected_income": 65000.0, "committed_outflows": 30649.0,
    "normal_discretionary_spend": 8629.0, "free_cash": 25722.0,
    "cash_after_purchase": -39278.0, "months_to_save": 3,
    "goal_impacts": [
        {"goal": "Emergency fund", "goal_id": "g1", "target_amount": 200000.0,
         "remaining": 125000.0, "progress_pct": 37.5,
         "months_baseline": 5, "months_after_purchase": 8, "delay_months": 3,
         "impact": "delayed", "required_monthly_baseline": 20833.33,
         "required_monthly_scenario": 31666.67},
        {"goal": "New laptop", "goal_id": "g2", "target_amount": 60000.0,
         "remaining": 60000.0, "progress_pct": 0.0,
         "months_baseline": 3, "months_after_purchase": 5, "delay_months": 2,
         "impact": "delayed", "required_monthly_baseline": 20000.0,
         "required_monthly_scenario": 41666.67},
    ],
    "scenarios": [
        {"label": "Buy now", "amount": 65000.0, "cash_after_purchase": -39278.0,
         "months_to_save": None, "goal_delay_months": 3,
         "detail": "Fund the full amount from this month's free cash flow."},
        {"label": "Save 3 months, then buy", "amount": 65000.0,
         "cash_after_purchase": 12166.0, "months_to_save": 3,
         "goal_delay_months": 0,
         "detail": "Set aside \u20b925,722/month for 3 month(s)."},
    ],
    "assumptions": ["Free cash flow = latest month's income minus actual spending."],
    "warnings": [],
    "period": "Jun 2026",
}

RESULTS = {
    "evaluate_affordability": DECISION,
    "calculate_committed_budget": BUDGET,
    "get_financial_goals": GOALS,
}


def _grounding(payload: dict) -> str:
    return " ".join(
        [e.value for e in payload["evidence"]]
        + [c.value for c in payload["calculations"]]
        + payload["insights"])


class TestGroundedResponse:
    def test_decision_in_payload(self):
        payload = orchestrator.build_response(
            "afford_purchase", "Can I afford a \u20b965,000 laptop next month?", RESULTS)
        assert payload["decision"] is not None
        assert payload["decision"].verdict == "NOT_YET"
        assert payload["decision"].purchase_amount == 65000.0
        assert len(payload["decision"].scenarios) == 2
        assert len(payload["decision"].goal_impacts) == 2

    def test_answer_grounded(self):
        payload = orchestrator.build_response(
            "afford_purchase", "Can I afford a \u20b965,000 laptop next month?", RESULTS)
        grounding = _grounding(payload)
        assert not is_ungrounded(payload["answer"], grounding)

    def test_no_invented_financial_numbers(self):
        payload = orchestrator.build_response(
            "afford_purchase", "Can I afford a \u20b965,000 laptop next month?", RESULTS)
        grounding = re.sub(r"[\u20b9,]|,\s", "", _grounding(payload))
        for match in re.finditer(r"\d{1,3}(?:,\d{3})+|\d{4,}", payload["answer"]):
            bare = match.group(0).replace(",", "")
            if len(bare) >= 4 and not (len(bare) == 4 and 2020 <= int(bare) <= 2100):
                assert bare in grounding, f"invented figure {bare} in answer"


class FakeFailureProvider:
    provider = "fail"
    model = "fail-model"

    @property
    def configured(self):
        return True

    def classify(self, question):
        raise LLMError("transport down")

    def plan(self, question, intent):
        raise LLMError("transport down")

    def respond(self, question, context, retry_note=""):
        raise LLMError("transport down")


@pytest.fixture
def mock_agent_db(monkeypatch):
    monkeypatch.setattr("app.db.get_user_by_id", lambda uid: USER if uid == "user-1" else None)
    monkeypatch.setattr("app.db.create_agent_run", lambda uid, q, intent=None: "run-afford-1")
    monkeypatch.setattr("app.db.create_agent_tool_call", lambda run_id, tool, args: f"call-{tool}")
    monkeypatch.setattr("app.db.complete_agent_tool_call",
                        lambda call_id, output, status="completed", started_at=None: None)
    monkeypatch.setattr("app.db.complete_agent_run",
                        lambda run_id, status="completed", final_response=None, started_at=None: None)
    monkeypatch.setattr("app.db.create_action_draft",
                        lambda uid, atype, title, description="", payload=None: f"draft-{title[:4]}")


class TestOrchestratorFallback:
    def test_llm_failure_falls_back_to_deterministic_decision(self, monkeypatch, mock_agent_db):
        recorded: list[tuple[str, dict]] = []

        def fake_exec(tool_name, user_id, args):
            recorded.append((tool_name, dict(args)))
            if tool_name == "evaluate_affordability":
                return DECISION
            if tool_name == "calculate_committed_budget":
                return BUDGET
            if tool_name == "get_financial_goals":
                return GOALS
            return {"count": 0}

        monkeypatch.setattr("app.services.orchestrator.get_provider",
                            lambda: FakeFailureProvider())
        monkeypatch.setattr("app.services.orchestrator.tools.execute_tool", fake_exec)
        resp = orchestrator.run_agent(
            "user-1", "Can I afford a \u20b965,000 laptop next month?")
        assert resp.mode == "deterministic"
        assert resp.intent == "afford_purchase"
        assert resp.decision is not None
        assert resp.decision.verdict == "NOT_YET"
        # The deterministic parser supplied the amount — exactly one call.
        calls = [a for t, a in recorded if t == "evaluate_affordability"]
        assert calls == [{"amount": 65000.0}]
        assert any(s.tool == "responder (deterministic)" for s in resp.activity)

    def test_unparseable_amount_no_decision_tool(self, monkeypatch, mock_agent_db):
        called: list[str] = []

        def fake_exec(tool_name, user_id, args):
            called.append(tool_name)
            if tool_name == "calculate_committed_budget":
                return BUDGET
            if tool_name == "get_financial_goals":
                return GOALS
            return {"count": 0}

        monkeypatch.setattr("app.services.orchestrator.get_provider",
                            lambda: FakeFailureProvider())
        monkeypatch.setattr("app.services.orchestrator.tools.execute_tool", fake_exec)
        resp = orchestrator.run_agent(
            "user-1", "Can I afford this purchase without delaying my laptop goal?")
        assert resp.intent == "afford_purchase"
        assert "evaluate_affordability" not in called  # never executed
        assert resp.decision is None
        assert resp.mode == "deterministic"