"""Synthetic demo data generation and validation (Phase 3).

Deterministic (fixed seed) Indian/INR transactions for ONE demo user,
~6 months of history. No real personal financial data is used here.

Scope: data foundation only. no financial calculations.
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

DEMO_USER_ID = "11111111-1111-1111-1111-111111111111"
TRANSACTION_TYPES = {"income", "expense"}


def generate_transactions(seed: int = 2026, month_count: int = 6) -> list[dict]:
    """Generate synthetic transactions for one demo user (INR)."""
    rng = random.Random(seed)
    rows: list[dict] = []
    txn = 0
    today = date(2026, 1, 1)  # pinned, deterministic anchor
    start = today.replace(day=1)
    # Netflix price increase month: 499 -> 649 from month 4 (April 2026).
    price_inc_month = _add_months(start, 3)

    for m in range(month_count):
        ym = _add_months(start, m)
        salary = _day(ym, 1)
        rows.append(_row(txn, "salary", "Monthly salary credit", "ACME Corp", 65000, "income", salary)); txn += 1
        rows.append(_row(txn, "rent", "House rent", "Landlord", 15000, "expense", _day(ym, 3))); txn += 1
        rows.append(_row(txn, "emi", "Car EMI", "HDFC Bank", 12500, "expense", _day(ym, 5))); txn += 1
        rows.append(_row(txn, "utilities", "Electricity bill", "BESCOM", 2200 + rng.randint(0, 700), "expense", _day(ym, 7))); txn += 1
        rows.append(_row(txn, "groceries", "Monthly groceries", "Vijay Sales", rng.randint(3500, 6500), "expense", _day(ym, 9))); txn += 1
        rows.append(_row(txn, "transport", "Fuel / Metro", "IndianOil", rng.randint(1200, 2600), "expense", _day(ym, 12))); txn += 1
        rows.append(_row(txn, "food", "Zomato / Swiggy", "Zomato", rng.randint(300, 1600), "expense", _day(ym, 15))); txn += 1
        rows.append(_row(txn, "entertainment", "Movie / OTT", "PVR", rng.randint(250, 900), "expense", _day(ym, 18))); txn += 1
        rows.append(_row(txn, "shopping", "Shopping", "Myntra", rng.randint(500, 3000), "expense", _day(ym, 21))); txn += 1

        # Subscription Guardian demo: Netflix paid monthly on the 10th.
        # Price increase 499 -> 649 from month 4 (April 2026) onward.
        # Month 6 (June 2026) has no Netflix transaction yet (billing cycle
        # next_payment_date = 2026-07-10), which keeps the June analytics
        # (and therefore the Phase 6 affordability hero) byte-identical.
        if m <= 4:
            netflix_amount = 649 if ym >= price_inc_month else 499
            rows.append(_row(txn, "subscriptions", "Netflix", "Netflix",
                             netflix_amount, "expense", _day(ym, 10)))
            txn += 1

    # One anomalous month: large one-off purchase (₹45,000 laptop) in month 5
    anomaly = _add_months(start, 4)
    rows.append(_row(txn, "electronics", "Laptop purchase", "Croma", 45000, "expense", _day(anomaly, 20))); txn += 1

    rows.sort(key=lambda r: r["date"])
    for i, r in enumerate(rows):
        r["transaction_id"] = f"txn_{i + 1:04d}"
    return rows


def _valid_values() -> dict:
    return {}


def _add_months(d: date, n: int) -> date:
    y, m = d.year + (d.month - 1 + n) // 12, (d.month - 1 + n) % 12 + 1
    return date(y, m, 1)


def _day(ym: date, day: int) -> date:
    return ym.replace(day=min(day, 28))


def _parse_date(iso: str) -> date:
    return date.fromisoformat(iso)


def _row(txn: int, category: str, description: str, merchant: str, amount: int, type_: str, d: date) -> dict:
    return {
        "transaction_id": f"txn_{txn + 1:04d}",
        "date": d.isoformat(),
        "category": category,
        "description": description,
        "merchant": merchant,
        "amount": amount,
        "type": type_,
        "user_id": DEMO_USER_ID,
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["transaction_id", "date", "category", "description", "merchant", "amount", "type", "user_id"])
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r[k] for k in writer.fieldnames})


def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise DemoDataLoadError(f"Demo data not found: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class DemoDataLoadError(Exception):
    pass


def validate_rows(rows: list[dict]) -> list[str]:
    """Return a list of errors (empty means valid)."""
    errors: list[str] = []
    seen: set = set()
    for i, r in enumerate(rows, start=1):
        rid = r.get("transaction_id", "")
        if not rid:
            errors.append(f"row {i}: missing transaction_id")
        elif rid in seen:
            errors.append(f"row {i}: duplicate transaction_id {rid}")
        seen.add(rid)
        if r.get("user_id") != DEMO_USER_ID:
            errors.append(f"row {i}: inconsistent user_id {r.get('user_id')!r}")
        try:
            _parse_date(r["date"])
        except Exception:
            errors.append(f"row {i}: invalid date {r.get('date')!r}")
        if r.get("type") not in TRANSACTION_TYPES:
            errors.append(f"row {i}: invalid type {r.get('type')!r}")
        try:
            amt = float(r["amount"])
            if amt <= 0:
                errors.append(f"row {i}: amount must be positive, got {amt}")
        except Exception:
            errors.append(f"row {i}: invalid amount {r.get('amount')!r}")
        if not r.get("category"):
            errors.append(f"row {i}: missing category")
    return errors