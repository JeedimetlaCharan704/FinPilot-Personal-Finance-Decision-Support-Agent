"""Unit tests for the monthly analytics engine (DB fully mocked)."""
from __future__ import annotations

import pytest

from app.services import analytics

C_RENT = "c-rent"
C_FOOD = "c-food"
C_SALARY = "c-salary"
C_COFFEE = "c-coffee"

CATEGORIES = [
    {"id": C_RENT, "name": "Rent", "category_type": "essential"},
    {"id": C_FOOD, "name": "Food", "category_type": "discretionary"},
    {"id": C_SALARY, "name": "Salary", "category_type": "income"},
    {"id": C_COFFEE, "name": "Coffee", "category_type": "discretionary"},
]

RECURRING = [
    {"id": "r-rent", "merchant": "Landlord", "amount": 15000,
     "frequency": "monthly", "next_payment_date": "2026-07-01", "status": "active"},
    {"id": "r-netflix", "merchant": "Netflix", "amount": 649,
     "frequency": "monthly", "next_payment_date": "2026-07-15", "status": "active"},
]

MONTH_TXNS = {
    # (year, month) -> transactions
    (2026, 5): [
        {"id": "t-salary-5", "category_id": C_SALARY, "transaction_date": "2026-05-01",
         "amount": 65000, "transaction_type": "income", "description": "Salary", "merchant": "Employer"},
        {"id": "t-rent-5", "category_id": C_RENT, "transaction_date": "2026-05-01",
         "amount": 15000, "transaction_type": "expense", "description": "Rent", "merchant": "Landlord"},
        {"id": "t-food-5", "category_id": C_FOOD, "transaction_date": "2026-05-10",
         "amount": 3000, "transaction_type": "expense", "description": "Groceries", "merchant": "DMart"},
    ],
    (2026, 6): [
        {"id": "t-salary-6", "category_id": C_SALARY, "transaction_date": "2026-06-01",
         "amount": 65000, "transaction_type": "income", "description": "Salary", "merchant": "Employer"},
        {"id": "t-rent-6", "category_id": C_RENT, "transaction_date": "2026-06-01",
         "amount": 15000, "transaction_type": "expense", "description": "Rent", "merchant": "Landlord"},
        {"id": "t-food-6", "category_id": C_FOOD, "transaction_date": "2026-06-10",
         "amount": 4800, "transaction_type": "expense", "description": "Groceries", "merchant": "DMart"},
        {"id": "t-coffee-6", "category_id": C_COFFEE, "transaction_date": "2026-06-12",
         "amount": 200, "transaction_type": "expense", "description": "Coffee", "merchant": "Cafe"},
    ],
}


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    def fake_fetch_transactions(user_id, start_date=None, end_date=None,
                                limit=None, columns=None):
        # resolve month from start_date "YYYY-MM-DD"
        if start_date:
            key = (int(start_date[:4]), int(start_date[5:7]))
        else:
            key = (2026, 6)
        return MONTH_TXNS.get(key, [])

    monkeypatch.setattr("app.db.list_categories", lambda: CATEGORIES)
    monkeypatch.setattr("app.db.fetch_transactions", fake_fetch_transactions)
    monkeypatch.setattr("app.db.fetch_recurring",
                        lambda user_id, status="active": RECURRING)


def test_monthly_summary_values(mock_db):
    s = analytics.monthly_summary("user-1", 2026, 6)
    assert s["has_data"] is True
    assert s["income"] == 65000
    assert s["expenses"] == 20000
    assert s["net"] == 45000
    assert round(s["savings_rate"], 2) == round(45000 / 65000 * 100, 2)
    assert s["committed"] == 15649  # 15000 + 649
    assert s["transactions_analyzed"] == 4


def test_monthly_summary_category_breakdown_sorted(mock_db):
    s = analytics.monthly_summary("user-1", 2026, 6)
    cats = s["category_breakdown"]
    assert cats[0]["category"] == "Rent" and cats[0]["amount"] == 15000
    assert cats[1]["category"] == "Food" and cats[1]["amount"] == 4800
    assert cats[2]["category"] == "Coffee" and cats[2]["amount"] == 200


def test_month_over_month_delta(mock_db):
    s = analytics.monthly_summary("user-1", 2026, 6)
    food = s["month_over_month"]["Food"]
    assert food["current"] == 4800
    assert food["previous"] == 3000
    assert food["diff"] == 1800
    assert food["percentage"] == 60.0


def test_category_breakdown_endpoint_shape(mock_db):
    out = analytics.category_breakdown("user-1", start_date="2026-06-01",
                                       end_date="2026-06-30")
    assert out["total_expenses"] == 20000
    assert len(out["categories"]) == 3


def test_recurring_analysis(mock_db):
    out = analytics.recurring_analysis("user-1")
    assert out["payment_count"] == 2
    assert out["monthly_committed"] == 15649
    assert out["annualized_recurring_cost"] == 15649 * 12


def test_budget_status(mock_db):
    b = analytics.budget_status("user-1", 2026, 6)
    assert b["income"] == 65000
    assert b["committed"] == 15649
    assert b["spent"] == 20000
    assert b["available"] == 65000 - 15649
    assert b["discretionary"] == 65000 - 15649 - 20000