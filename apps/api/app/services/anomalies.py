# Deterministic anomaly detection (Phase 4). Explainable thresholds only.
#
# Signals:
#   category_spike     - category spending vs previous 3-month average
#   spend_spike        - total expense vs previous month
#   large_transaction  - single expense > floor AND > 3x median expense
#   duplicate          - same merchant + amount within 2 days
#   recurring_like     - same merchant, similar amount, in 2+ consecutive months
#                         that is NOT already in the recurring_payments table
from __future__ import annotations

from datetime import date, timedelta

from app import db
from app.services.analytics import (
    _f2, _period_bounds, _prev_period, categories_map, monthly_summary,
)

CATEGORY_SPIKE_PCT = 50.0      # >50% above baseline is a spike
CATEGORY_MIN_DIFF = 500.0      # ...and at least INR 500 absolute
SPEND_SPIKE_PCT = 50.0
SPEND_SPIKE_MIN_DIFF = 2000.0
LARGE_TXN_MIN = 15000.0        # hard floor for a "large" transaction
LARGE_TXN_MEDIAN_MULT = 3.0
DUPLICATE_DAY_WINDOW = 2
RECURRING_AMOUNT_TOLERANCE = 0.10


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _month_ago_periods(year: int, month: int, count: int) -> list[tuple[int, int]]:
    periods = []
    y, m = year, month
    for _ in range(count):
        y, m = _prev_period(y, m)
        periods.append((y, m))
    return periods


def detect_anomalies(user_id: str, year: int | None = None,
                     month: int | None = None) -> dict:
    base = monthly_summary(user_id, year, month)
    if not base["has_data"]:
        return {"period": None, "anomalies": [], "has_data": False}
    year, month = base["year"], base["month"]
    anomalies: list[dict] = []

    cur_start, cur_end = _period_bounds(year, month)
    cur_txns = db.fetch_transactions(
        user_id, start_date=cur_start, end_date=cur_end,
        columns="id,category_id,transaction_date,amount,transaction_type,description,merchant")
    cmap = categories_map()

    # 1. category spike vs previous 3-month average ------------------------
    baseline_pool = []
    for (py, pm) in _month_ago_periods(year, month, 3):
        s, e = _period_bounds(py, pm)
        baseline_pool += db.fetch_transactions(
            user_id, start_date=s, end_date=e,
            columns="id,category_id,transaction_date,amount,transaction_type,merchant")

    cat_current: dict[str, float] = {}
    cat_refs: dict[str, list[str]] = {}
    for t in cur_txns:
        if t["transaction_type"] != "expense":
            continue
        name = cmap.get(t.get("category_id"), "Other")
        cat_current[name] = cat_current.get(name, 0.0) + float(t["amount"])
        cat_refs.setdefault(name, []).append(t["id"])

    cat_baseline: dict[str, float] = {}
    for t in baseline_pool:
        if t["transaction_type"] != "expense":
            continue
        name = cmap.get(t.get("category_id"), "Other")
        cat_baseline[name] = cat_baseline.get(name, 0.0) + float(t["amount"])

    for name, actual in cat_current.items():
        avg = cat_baseline.get(name, 0.0) / 3.0
        diff = actual - avg
        pct = (diff / avg * 100.0) if avg > 0 else None
        if pct is not None and pct >= CATEGORY_SPIKE_PCT and diff >= CATEGORY_MIN_DIFF:
            anomalies.append({
                "type": "category_spike", "severity": "high" if pct >= 100 else "medium",
                "category": name, "actual": _f2(actual), "baseline": _f2(avg),
                "difference": _f2(diff), "percentage": _f2(pct),
                "threshold": f">={CATEGORY_SPIKE_PCT:.0f}% above 3-month average "
                             f"and >= INR {CATEGORY_MIN_DIFF:,.0f}",
                "explanation": (f"{name} spending is {pct:.0f}% higher than the "
                                f"previous 3-month average of {_inr(avg)}."),
                "references": cat_refs.get(name, []),
            })

    # 2. total spend spike vs previous month --------------------------------
    py, pm = _prev_period(year, month)
    prev_sum = monthly_summary(user_id, py, pm)
    if prev_sum["has_data"] and prev_sum["expenses"] > 0:
        diff = base["expenses"] - prev_sum["expenses"]
        pct = diff / prev_sum["expenses"] * 100.0
        if pct >= SPEND_SPIKE_PCT and diff >= SPEND_SPIKE_MIN_DIFF:
            anomalies.append({
                "type": "spend_spike", "severity": "medium",
                "category": "Total spending",
                "actual": _f2(base["expenses"]), "baseline": _f2(prev_sum["expenses"]),
                "difference": _f2(diff), "percentage": _f2(pct),
                "threshold": f">={SPEND_SPIKE_PCT:.0f}% vs previous month and >= INR {SPEND_SPIKE_MIN_DIFF:,.0f}",
                "explanation": (f"Total spending is {pct:.0f}% higher than last month "
                                f"({_inr(prev_sum['expenses'])} -> {_inr(base['expenses'])})."),
                "references": [],
            })

    # 3. large single transaction -------------------------------------------
    # Known recurring payments (rent, EMI, Netflix...) are expected, not anomalies.
    known_merchants = {r["merchant"].strip().lower()
                       for r in db.fetch_recurring(user_id)}
    amounts = [float(t["amount"]) for t in cur_txns if t["transaction_type"] == "expense"]
    med = _median(amounts)
    for t in cur_txns:
        if t["transaction_type"] != "expense":
            continue
        if (t.get("merchant") or "").strip().lower() in known_merchants:
            continue
        amt = float(t["amount"])
        if amt >= LARGE_TXN_MIN and (med <= 0 or amt >= LARGE_TXN_MEDIAN_MULT * med):
            anomalies.append({
                "type": "large_transaction", "severity": "medium",
                "category": cmap.get(t.get("category_id"), "Other"),
                "actual": _f2(amt), "baseline": _f2(med),
                "difference": _f2(amt - med), "percentage": None,
                "threshold": f">= INR {LARGE_TXN_MIN:,.0f} and >= {LARGE_TXN_MEDIAN_MULT:.0f}x "
                             f"median expense ({_inr(med)})",
                "explanation": (f"Single {_inr(amt)} transaction at "
                                f"{t.get('merchant') or t.get('description', '?')} is "
                                f"{LARGE_TXN_MEDIAN_MULT:.0f}x your median expense."),
                "references": [t["id"]],
            })

    # 4. duplicate transactions (same merchant, amount, within 2 days) ------
    seen: dict[tuple, tuple[date, str]] = {}
    for t in sorted(cur_txns, key=lambda x: x["transaction_date"]):
        if t["transaction_type"] != "expense":
            continue
        key = (t.get("merchant") or t.get("description", "").lower(), float(t["amount"]))
        if key in seen:
            d1, first_id = seen[key]
            d2 = date.fromisoformat(t["transaction_date"])
            if abs((d2 - d1).days) <= DUPLICATE_DAY_WINDOW:
                anomalies.append({
                    "type": "duplicate", "severity": "low",
                    "category": cmap.get(t.get("category_id"), "Other"),
                    "actual": _f2(float(t["amount"])), "baseline": _f2(float(t["amount"])),
                    "difference": 0.0, "percentage": 0.0,
                    "threshold": f"merchant + amount repeated within {DUPLICATE_DAY_WINDOW} days",
                    "explanation": (f"Possible duplicate: {t.get('merchant') or 'unknown merchant'} "
                                    f"for {_inr(float(t['amount']))} appears twice within "
                                    f"{DUPLICATE_DAY_WINDOW} days."),
                    "references": [first_id, t["id"]],
                })
        else:
            seen[key] = (date.fromisoformat(t["transaction_date"]), t["id"])

    # 5. recurring-like payments not in the recurring table -----------------
    known = {r["merchant"].strip().lower() for r in db.fetch_recurring(user_id)}
    by_merchant: dict[str, list[dict]] = {}
    for t in cur_txns + baseline_pool:
        if t["transaction_type"] != "expense":
            continue
        merchant = (t.get("merchant") or "").strip().lower()
        if not merchant:
            continue
        by_merchant.setdefault(merchant, []).append(t)
    for merchant, txns in by_merchant.items():
        if merchant in known:
            continue
        # must span at least TWO distinct months (same-month repeats are dups)
        months = {t["transaction_date"][:7] for t in txns}
        if len(months) < 2:
            continue
        amounts = sorted(float(t["amount"]) for t in txns)
        if len(amounts) >= 2 and \
           abs(amounts[-1] - amounts[0]) <= RECURRING_AMOUNT_TOLERANCE * amounts[-1]:
            anomalies.append({
                "type": "recurring_like", "severity": "low",
                "category": cmap.get(txns[0].get("category_id"), "Other"),
                "actual": _f2(amounts[-1]), "baseline": _f2(amounts[-1]),
                "difference": 0.0, "percentage": None,
                "threshold": "same merchant, similar amount, 2+ months in a row, not in recurring table",
                "explanation": (f"{txns[0].get('merchant')} looks like a recurring payment "
                                f"({_inr(amounts[-1])} on {len(txns)} occasions) but is not "
                                f"tracked in your recurring payments."),
                "references": [t["id"] for t in txns],
            })

    return {"period": f"{year:04d}-{month:02d}", "anomalies": anomalies,
            "has_data": True, "count": len(anomalies)}



def _inr(v: float) -> str:
    return f"\u20b9{v:,.0f}"