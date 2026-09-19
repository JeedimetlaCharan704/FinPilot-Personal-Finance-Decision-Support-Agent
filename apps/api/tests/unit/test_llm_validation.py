"""Unit tests for LLM structured-output validation (Phase 5).

The LLM is untrusted: unknown intents, unknown tools, unknown arguments,
malformed types and prompt injections must all be rejected here.
"""
from __future__ import annotations

import pytest

from app.llm.schemas import LLMAnswerOut, LLMIntentOut, LLMToolPlan
from app.llm.validation import (
    extract_json_text,
    is_ungrounded,
    validate_answer,
    validate_intent,
    validate_tool_plan,
)


class TestExtractJson:
    def test_plain_json(self):
        assert extract_json_text('{"a": 1}') == '{"a": 1}'

    def test_fenced_json(self):
        text = 'Here you go:\n```json\n{"intent": "overview"}\n```\nDone.'
        assert extract_json_text(text) == '{"intent": "overview"}'

    def test_prose_around_json(self):
        text = 'The answer {"intent": "spend_most", "x": 1} is final.'
        assert extract_json_text(text) == '{"intent": "spend_most", "x": 1}'

    def test_no_json(self):
        assert extract_json_text("no braces here") == ""


class TestValidateIntent:
    def test_valid_intent(self):
        out = validate_intent({"intent": "spend_most", "reason": "r", "confidence": 0.9})
        assert isinstance(out, LLMIntentOut)
        assert out.intent == "spend_most"

    def test_valid_intent_from_json_string(self):
        out = validate_intent('{"intent": "anomaly", "confidence": 0.7}')
        assert out is not None and out.intent == "anomaly"

    def test_invalid_intent_rejected(self):
        assert validate_intent({"intent": "give_me_my_bank_password"}) is None

    def test_non_dict_rejected(self):
        assert validate_intent("[1, 2, 3]") is None
        assert validate_intent("garbage!!") is None
        assert validate_intent(None) is None

    def test_missing_intent_rejected(self):
        assert validate_intent({"reason": "no intent key"}) is None


class TestValidateToolPlan:
    def test_valid_plan(self):
        plan = {
            "intent": "afford_purchase",
            "reason": "check affordability",
            "tools": [
                {"name": "calculate_committed_budget", "arguments": {}},
                {"name": "simulate_expense_change", "arguments": {"amount": 65000}},
            ],
        }
        out = validate_tool_plan(plan)
        assert isinstance(out, LLMToolPlan)
        assert [t.name for t in out.tools] == ["calculate_committed_budget",
                                               "simulate_expense_change"]

    def test_unknown_tool_rejected(self):
        plan = {"intent": "overview",
                "tools": [{"name": "read_bank_balance_directly", "arguments": {}}]}
        assert validate_tool_plan(plan) is None

    def test_unknown_argument_rejected(self):
        plan = {"intent": "overview",
                "tools": [{"name": "get_monthly_summary", "arguments": {"secret_key": 1}}]}
        assert validate_tool_plan(plan) is None

    def test_prompt_injection_tool_rejected(self):
        plan = {"intent": "overview", "tools": [{"name": "execute_python", "arguments": {}}]}
        assert validate_tool_plan(plan) is None

    def test_malformed_arguments_rejected(self):
        # amount must be a positive number; strings/negatives/booleans rejected
        for bad in ({"amount": "65000"}, {"amount": -5}, {"amount": True},
                    {"amount": 0}, {"amount": 10_000_000}):
            plan = {"intent": "afford_purchase",
                    "tools": [{"name": "simulate_expense_change", "arguments": bad}]}
            assert validate_tool_plan(plan) is None, bad

    def test_non_dict_arguments_rejected(self):
        plan = {"intent": "overview",
                "tools": [{"name": "get_monthly_summary", "arguments": [1, 2]}]}
        assert validate_tool_plan(plan) is None

    def test_nested_args_rejected(self):
        plan = {"intent": "overview",
                "tools": [{"name": "get_transactions",
                           "arguments": {"limit": {"crafted": "object"}}}]}
        assert validate_tool_plan(plan) is None

    def test_empty_plan_rejected(self):
        assert validate_tool_plan({"intent": "overview", "tools": []}) is None

    def test_invalid_intent_rejected(self):
        plan = {"intent": "not_a_real_intent",
                "tools": [{"name": "get_monthly_summary", "arguments": {}}]}
        assert validate_tool_plan(plan) is None

    def test_valid_arg_ranges(self):
        plan = {"intent": "overview", "tools": [
            {"name": "get_transactions", "arguments": {"limit": 100}},
            {"name": "get_upcoming_obligations", "arguments": {"days": 30}},
            {"name": "get_monthly_summary", "arguments": {"year": 2026, "month": 6}},
        ]}
        assert validate_tool_plan(plan) is not None


class TestValidateAnswer:
    def test_valid_answer(self):
        out = validate_answer({"answer": "Rent was your top category.", "warnings": []})
        assert isinstance(out, LLMAnswerOut)
        assert "Rent" in out.answer

    def test_valid_answer_from_fenced_json(self):
        text = '```json\n{"answer": "Yes, feasible.", "uncertainty": null}\n```'
        out = validate_answer(text)
        assert out is not None and out.answer == "Yes, feasible."

    def test_missing_answer_rejected(self):
        assert validate_answer({"warnings": []}) is None
        assert validate_answer({"answer": ""}) is None
        assert validate_answer("not json") is None

    def test_answer_truncated_to_cap(self):
        long_ans = "x" * 5000
        out = validate_answer({"answer": long_ans})
        assert out is not None and len(out.answer) <= 2000


class TestEvidenceGrounding:
    def test_grounded_answer_passes(self):
        context = "Rent 15000 Income 65000 savings_rate 76.9% period Jun 2026"
        answer = "Rent was ₹15,000 this month, income ₹65,000."
        assert is_ungrounded(answer, context) is False

    def test_invented_figure_detected(self):
        context = "Rent 15000 Income 65000"
        answer = "Your net worth jumped to ₹9,999,999 this month."
        assert is_ungrounded(answer, context) is True

    def test_small_counts_ignored(self):
        context = "Rent 15000"
        answer = "You have 12 transactions and 3 anomalies."
        assert is_ungrounded(answer, context) is False

    def test_calendar_year_not_financial(self):
        context = "Rent 15000"
        answer = "In Jun 2026, Rent was 15000."
        assert is_ungrounded(answer, context) is False

    def test_empty_context_flagged(self):
        assert is_ungrounded("Rent 15000", "") is True