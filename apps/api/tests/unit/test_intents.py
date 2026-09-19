"""Unit tests for the NL intent router (categories mocked for lookup)."""
from __future__ import annotations

import pytest

from app.services import intents

CATEGORIES = [
    {"id": "c1", "name": "Food", "category_type": "discretionary"},
    {"id": "c2", "name": "Rent", "category_type": "essential"},
    {"id": "c3", "name": "Shopping", "category_type": "discretionary"},
]


@pytest.fixture(autouse=True)
def mock_categories(monkeypatch):
    monkeypatch.setattr("app.db.list_categories", lambda: CATEGORIES)


CASES = [
    ("Where did I spend the most this month?", "spend_most"),
    ("Where did my money go?", "spend_most"),
    ("How much did I spend on food?", "category_amount"),
    ("What subscriptions am I paying for?", "subscriptions"),
    ("What increased compared with last month?", "what_changed"),
    ("What changed this month?", "what_changed"),
    ("Can I afford a 60000 rupee laptop?", "afford_purchase"),
    ("Should I buy an iPhone?", "afford_purchase"),
    ("How much of my income is already committed?", "committed"),
    ("How much do I need to save each month for my emergency fund?", "goal_save"),
    ("What happens if my rent increases by 2000?", "rent_increase"),
    ("Which recurring payments are coming up?", "upcoming"),
    ("Am I on track for my emergency fund?", "goal_track"),
    ("Why is my electricity bill so high?", "anomaly"),
]


@pytest.mark.parametrize("question,expected", CASES)
def test_intent_routing(question, expected):
    info = intents.classify(question)
    assert info["intent"] == expected, f"{question!r} -> {info['intent']}"
    assert info["tools"], "every intent must plan at least one tool"


def test_every_intent_has_nonempty_tools():
    for name, _, tools in intents._INTENT_PATTERNS:
        assert tools, name


def test_fallback_intent():
    info = intents.classify("hello there")
    assert info["intent"] == "overview"
    assert info["confidence"] < 0.5