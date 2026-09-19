"""Unit tests for deterministic anomaly detection (DB mocked)."""
from __future__ import annotations

import pytest

from app.services import anomalies, analytics

C_RENT = "c-rent"
C_FOOD = "c-food"
C_COFFEE = "c-coffee"
C_GYM = "c-gym"
C_OTHER = "c-other"

CATEGORIES = [
    {"id": C_RENT, "name": "Rent", "category_type": "essential"},
    {"id": C_FOOD, "name": "Food", "category_type": "discretionary"},
    {"id": C_COFFEE, "name": "Coffee", "category_type": "discretionary"},
    {"id": C_GYM, "name": "Gym", "category_type": "discretionary"},
    {"id": C_OTHER, "name": "Other", "category_type": "discretionary"},
]

RECURRING = [
    {"id": "r-rent", "merchant": "Landlord", "amount": 15000,
     "frequency": "monthly", "next_payment_date": "2026-07-01", "status": "active"},
]

BASE = {"id": "t", "category_id": None, "transaction_date": "2026-XX-01",
        "amount": 0, "transaction_type": "expense", "description": "", "merchant": ""}


def txn(tid, category, day, amount, merchant="M", typ="expense", month="06"):
    return {"id": tid, "category_id": category,
            "transaction_date": f"2026-{month}-{day:02d}", "amount": amount,
            "transaction_type": typ, "description": "", "merchant": merchant}


MONTHS = {
    (2026, 3): [
        txn("a1", C_RENT, 1, 15000, "Landlord", month="03"),
        txn("a2", C_FOOD, 5, 3000, "DMart", month="03"),
    ],
    (2026, 4): [
        txn("b1", C_RENT, 1, 15000, "Landlord", month="04"),
        txn("b2", C_FOOD, 5, 3000, "DMart", month="04"),
    ],
    (2026, 5): [
        txn("c1", C_RENT, 1, 15000, "Landlord", month="05"),
        txn("c2", C_FOOD, 5, 3000, "DMart", month="05"),
        txn("c3", C_GYM, 10, 1500, "GymFit", month="05"),
    ],
    (2026, 6): [
        txn("d1", C_RENT, 1, 15000, "Landlord", month="06"),
        txn("d2", C_FOOD, 5, 4800, "DMart", month="06"),
        txn("d3", C_COFFEE, 6, 200, "Cafe", month="06"),
        txn("d4", C_COFFEE, 7, 200, "Cafe", month="06"),       # duplicate
        txn("d5", C_GYM, 10, 1500, "GymFit", month="06"),      # recurring-like
        txn("d6", C_OTHER, 12, 20000, "BigSpend", month="06"),  # large txn (own category)
    ],
}


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    def fake_fetch(user_id, start_date=None, end_date=None, limit=None, columns=None):
        if start_date:
            key = (int(start_date[:4]), int(start_date[5:7]))
        else:
            key = (2026, 6)
        return MONTHS.get(key, [])

    monkeypatch.setattr("app.db.list_categories", lambda: CATEGORIES)
    monkeypatch.setattr("app.db.fetch_transactions", fake_fetch)
    monkeypatch.setattr("app.db.fetch_recurring",
                        lambda user_id, status="active": RECURRING)


def test_category_spike_detected(mock_db):
    out = anomalies.detect_anomalies("user-1", 2026, 6)
    spikes = [a for a in out["anomalies"] if a["type"] == "category_spike"]
    assert spikes, "expected a category spike"
    s = spikes[0]
    assert s["category"] == "Food"
    assert s["actual"] == 4800
    assert round(s["baseline"], 1) == 3000   # avg over Mar/Apr/May
    assert s["percentage"] == 60.0
    assert s["references"]  # transaction ids attached


def test_duplicate_detected(mock_db):
    out = anomalies.detect_anomalies("user-1", 2026, 6)
    dups = [a for a in out["anomalies"] if a["type"] == "duplicate"]
    assert dups
    assert "d3" in dups[0]["references"] and "d4" in dups[0]["references"]


def test_large_transaction_detected(mock_db):
    out = anomalies.detect_anomalies("user-1", 2026, 6)
    big = [a for a in out["anomalies"] if a["type"] == "large_transaction"]
    assert big
    assert big[0]["actual"] == 20000
    assert "d6" in big[0]["references"]


def test_recurring_like_detected(mock_db):
    out = anomalies.detect_anomalies("user-1", 2026, 6)
    rl = [a for a in out["anomalies"] if a["type"] == "recurring_like"]
    assert rl
    assert rl[0]["actual"] == 1500
    assert "GymFit" in rl[0]["explanation"]


def test_explanations_are_grounded(mock_db):
    out = anomalies.detect_anomalies("user-1", 2026, 6)
    for a in out["anomalies"]:
        assert a["explanation"]
        assert a["threshold"]