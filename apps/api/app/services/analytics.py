# Monthly financial intelligence engine (Phase 4).
#
# Everything here is computed from the database with SQL-filtered reads and
# deterministic Python aggregation. No LLM, no fabrication, no rounding drift.
from __future__ import annotations

import threading
import time
from calendar import monthrange
from datetime import date, datetime, timedelta

from app import db

FREQ_MONTHLY_MULT = {
    "weekly": 52 / 12,     # ~4.333 transactions per month
    "monthly": 1.0,
    "quarterly": 1 / 3,
    "yearly": 1 / 12,
}

_TXN_COLUMNS = "id,category_id,transaction_date,amount,transaction_type,description,merchant"


def _f2(v: float) -> float:
    return round(float(v), 2)


def _period_bounds(year: int, month: int) -> tuple[str, str]:
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])
    return first.isoformat(), last.isoformat()


def _prev_period(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


_cache_lock = threading.Lock()
_cache: dict[str, tuple[float, object]] = {}
_CACHE_TTL_SECONDS = 60.0


def _ttl_cache(key: str, loader):
    """Tiny thread-safe TTL cache for deterministic, rarely-changing data."""
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < _CACHE_TTL_SECONDS:
            return hit[1]
    value = loader()
    with _cache_lock:
        _cache[key] = (now, value)
    return value


def categories_map() -> dict[str, str]:
    return _ttl_cache("categories", lambda: {r["id"]: r["name"] for r in db.list_categories()})


def committed_monthly(user_id: str) -> float:
    return _ttl_cache(f"committed:{user_id}",
                      lambda: _committed_once(user_id))


def _committed_once(user_id: str) -> float:
    total = 0.0
    for r in db.fetch_recurring(user_id, status="active"):
        total += float(r["amount"]) * FREQ_MONTHLY_MULT.get(r["frequency"], 1.0)
    return _f2(total)


def latest_period(user_id: str) -> tuple[int, int] | None:
    """Most recent (year, month) that has transactions for this user."""
    rows = db.fetch_transactions(user_id, limit=1, columns="transaction_date")
    if not rows:
        return None
    raw = rows[0]["transaction_date"]  # ISO date string (sorted desc)
    return int(raw[:4]), int(raw[5:7])





def _aggregate_txns(user_id: str, start: str, end: str) -> dict:
    txns = db.fetch_transactions(user_id, start_date=start, end_date=end,
                                 columns=_TXN_COLUMNS)
    cmap = categories_map()
    income = 0.0
    expenses = 0.0
    cat_totals: dict[str, float] = {}
    cat_counts: dict[str, int] = {}
    for t in txns:
        amt = float(t["amount"])
        name = cmap.get(t.get("category_id"), "Other")
        if t["transaction_type"] == "income":
            income += amt
        else:
            expenses += amt
            cat_totals[name] = cat_totals.get(name, 0.0) + amt
            cat_counts[name] = cat_counts.get(name, 0) + 1
    return {
        "transactions": txns,
        "income": _f2(income),
        "expenses": _f2(expenses),
        "cat_totals": cat_totals,
        "cat_counts": cat_counts,
    }


def monthly_summary(user_id: str, year: int | None = None,
                    month: int | None = None) -> dict:
    """Full monthly intelligence report for the given (or latest) month."""
    if year is None or month is None:
        lp = latest_period(user_id)
        year, month = lp if lp else (datetime.now().year, datetime.now().month)
        if lp is None:
            return {"year": year, "month": month, "has_data": False,
                    "income": 0.0, "expenses": 0.0, "net": 0.0, "savings_rate": 0.0,
                    "committed": 0.0, "category_breakdown": [], "largest_expenses": [],
                    "month_over_month": {}, "insights": [], "transactions_analyzed": 0}

    start, end = _period_bounds(year, month)
    agg = _aggregate_txns(user_id, start, end)
    net = _f2(agg["income"] - agg["expenses"])
    savings_rate = _f2((net / agg["income"] * 100.0)) if agg["income"] > 0 else 0.0
    committed = committed_monthly(user_id)

    breakdown = [
        {"category": name, "amount": _f2(amt), "transaction_count": agg["cat_counts"].get(name, 0)}
        for name, amt in sorted(agg["cat_totals"].items(), key=lambda kv: kv[1], reverse=True)
    ]
    largest_expenses = sorted(
        (t for t in agg["transactions"] if t["transaction_type"] == "expense"),
        key=lambda t: float(t["amount"]), reverse=True,
    )[0:5]
    largest_expenses = [
        {"merchant": t.get("merchant") or t.get("description", "Expense"),
         "description": t.get("description", ""), "amount": _f2(float(t["amount"])),
         "date": t["transaction_date"], "transaction_id": t["id"]}
        for t in largest_expenses
    ]

    mom = {}
    py, pm = _prev_period(year, month)
    pstart, pend = _period_bounds(py, pm)
    pagg = _aggregate_txns(user_id, pstart, pend)
    for name in set(agg["cat_totals"]) | set(pagg["cat_totals"]):
        cur = agg["cat_totals"].get(name, 0.0)
        prev = pagg["cat_totals"].get(name, 0.0)
        diff = _f2(cur - prev)
        pct = _f2((diff / prev * 100.0)) if prev > 0 else None
        mom[name] = {"current": _f2(cur), "previous": _f2(prev), "diff": diff,
                     "percentage": pct}

    insights = []
    if breakdown:
        top = breakdown[0]
        insights.append(f"Largest category: {top['category']} at "
                        f"{_inr(top['amount'])} across {top['transaction_count']} transactions.")
    if mom:
        increases = [v for v in mom.values() if v.get("percentage") and v["percentage"] > 0]
        if increases:
            biggest = max(increases, key=lambda v: v["percentage"])
            insights.append(f"Largest increase: {biggest['percentage']:.0f}% "
                            f"({_inr(biggest['diff'])}) vs previous month.")
    if savings_rate > 0:
        insights.append(f"Savings rate for the period: {savings_rate:.1f}%.")

    return {
        "year": year, "month": month, "has_data": True,
        "period_label": f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][month-1]} {year}",
        "income": agg["income"], "expenses": agg["expenses"], "net": net,
        "savings_rate": savings_rate, "committed": committed,
        "category_breakdown": breakdown, "largest_expenses": largest_expenses,
        "month_over_month": mom, "insights": insights,
        "transactions_analyzed": len(agg["transactions"]),
    }


def category_breakdown(user_id: str, start_date: str | None = None,
                       end_date: str | None = None,
                       year: int | None = None, month: int | None = None) -> dict:
    if year is not None and month is not None:
        start_date, end_date = _period_bounds(year, month)
    if not start_date or not end_date:
        lp = latest_period(user_id)
        if lp:
            start_date, end_date = _period_bounds(*lp)
    agg = _aggregate_txns(user_id, start_date, end_date)
    return {
        "start_date": start_date, "end_date": end_date,
        "categories": [
            {"category": name, "amount": _f2(amt),
             "transaction_count": agg["cat_counts"].get(name, 0)}
            for name, amt in sorted(agg["cat_totals"].items(), key=lambda kv: kv[1], reverse=True)
        ],
        "total_expenses": _f2(agg["expenses"]),
    }


def compare_periods(user_id: str, year: int | None = None,
                    month: int | None = None) -> dict:
    """Month-over-month comparison (current vs previous month)."""
    if year is None or month is None:
        lp = latest_period(user_id)
        if not lp:
            return {"has_data": False}
        year, month = lp
    summary = monthly_summary(user_id, year, month)
    py, pm = _prev_period(year, month)
    prev = monthly_summary(user_id, py, pm)
    pct = ((summary["expenses"] - prev["expenses"]) / prev["expenses"] * 100) if prev["expenses"] > 0 else None
    return {
        "has_data": summary["has_data"],
        "current": {"year": year, "month": month, "income": summary["income"],
                    "expenses": summary["expenses"], "net": summary["net"],
                    "savings_rate": summary["savings_rate"]},
        "previous": {"year": py, "month": pm, "income": prev["income"],
                     "expenses": prev["expenses"], "net": prev["net"],
                     "savings_rate": prev["savings_rate"]},
        "expense_diff": _f2(summary["expenses"] - prev["expenses"]),
        "expense_pct_change": _f2(pct) if pct is not None else None,
        "categories": summary["month_over_month"],
    }


def recurring_analysis(user_id: str) -> dict:
    payments = db.fetch_recurring(user_id, status="active")
    today = date.today()
    items = []
    total_monthly = 0.0
    for p in payments:
        amount = float(p["amount"])
        mult = FREQ_MONTHLY_MULT.get(p["frequency"], 1.0)
        monthly = _f2(amount * mult)
        total_monthly += monthly
        nxt = p.get("next_payment_date")
        days_until = None
        if nxt:
            try:
                days_until = (date.fromisoformat(nxt) - today).days
            except ValueError:
                days_until = None
        items.append({
            "id": p["id"], "merchant": p["merchant"],
            "description": p.get("description", ""),
            "amount": _f2(amount), "frequency": p["frequency"],
            "next_payment_date": nxt, "days_until_next": days_until,
            "monthly_commitment": monthly,
            "annualized": _f2(monthly * 12),
        })
    items.sort(key=lambda x: (x["next_payment_date"] is None, x.get("next_payment_date") or ""))
    return {
        "payments": items,
        "monthly_committed": _f2(total_monthly),
        "annualized_recurring_cost": _f2(total_monthly * 12),
        "payment_count": len(items),
    }


def upcoming_obligations(user_id: str, days: int = 30) -> dict:
    today = date.today()
    horizon = today + timedelta(days=days)
    out = []
    for p in db.fetch_recurring(user_id, status="active"):
        nxt = p.get("next_payment_date")
        if not nxt:
            continue
        try:
            nd = date.fromisoformat(nxt)
        except ValueError:
            continue
        if today <= nd <= horizon:
            mult = FREQ_MONTHLY_MULT.get(p["frequency"], 1.0)
            out.append({
                "merchant": p["merchant"], "amount": _f2(float(p["amount"])),
                "frequency": p["frequency"],
                "monthly_commitment": _f2(float(p["amount"]) * mult),
                "next_payment_date": nxt,
                "days_until": (nd - today).days,
            })
    out.sort(key=lambda x: x["days_until"])
    return {"upcoming": out, "days_horizon": days, "count": len(out)}


def budget_status(user_id: str, year: int | None = None,
                  month: int | None = None) -> dict:
    """Budget commitment engine.

    committed        = recurring obligations in the period (assumption)
    spent            = actual expenses in the period
    available        = income - committed (assumes commitments are paid first)
    discretionary    = income - committed - spent (must be >= 0 to stay afloat)
    """
    summary = monthly_summary(user_id, year, month)
    income = summary["income"]
    committed = summary["committed"]
    spent = summary["expenses"]
    available = _f2(income - committed)
    discretionary = _f2(income - committed - spent)
    return {
        "year": summary["year"], "month": summary["month"],
        "has_data": summary["has_data"],
        "income": income, "committed": committed, "spent": spent,
        "available": available, "discretionary": discretionary,
        "monthly_savings": summary["net"],
        "assumptions": [
            "Committed = active recurring payments expressed per month.",
            "Available = income minus committed obligations.",
            "Discretionary = income minus committed minus actual spending.",
        ],
    }


def _inr(v: float) -> str:
    return f"\u20b9{v:,.0f}"