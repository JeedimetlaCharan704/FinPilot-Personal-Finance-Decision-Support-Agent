"""Subscription Guardian (Phase 7).

Deterministic subscription intelligence: watches a user's active recurring
payments, detects price changes from the actual transaction history, and
produces human-reviewable *drafts* of suggested actions.

Design contract
---------------
* Everything here is derived from persisted data only -- never fabricated,
  never guessed. All rupee figures are computed and rounded to 2 decimals.
* The Guardian NEVER cancels, contacts, or executes anything. It only
  drafts suggested actions that the user can approve or reject.
* Signals:
    PRICE_INCREASE    current monthly amount > the previous stable amount
                      (detected from the transaction history.change point)
    RECURRING_COST    the payment is an active recurring cost (base signal)
    HIGH_ANNUAL_COST  annual cost >= threshold for a non-essential category
* Fixed commitments (rent / emi / utilities) are only reported when they
  carry a PRICE_INCREASE signal, never as generic "review" targets.
"""
from __future__ import annotations

from datetime import date

from app import db
from app.services.analytics import categories_map

# frequency -> multiplier to express one payment as a monthly amount
_FREQ_MONTHLY_MULT: dict[str, float] = {
    "weekly": 52.0 / 12.0,
    "monthly": 1.0,
    "quarterly": 1.0 / 3.0,
    "yearly": 1.0 / 12.0,
}

# Fixed commitments: never suggested for cancellation/review just for existing.
_ESSENTIAL_CATEGORIES = frozenset({"rent", "emi", "utilities"})

# A recurring cost at/above this annualized amount is flagged HIGH_ANNUAL_COST
# (non-essential categories only).
_HIGH_ANNUAL_THRESHOLD = 24000.0

_SIGNAL_ORDER = ("PRICE_INCREASE", "HIGH_ANNUAL_COST", "RECURRING_COST")

_TXN_COLUMNS = "transaction_date,amount,transaction_type,merchant"


class GuardianError(Exception):
    """Raised for guardian-specific validation failures."""


def _f2(value: float) -> float:
    return round(float(value), 2)


def _merchant_history(user_id: str, merchant: str) -> list[dict]:
    """Chronological expense payments for one merchant (oldest first).

    Only months where the payment actually happened appear here, so a
    subscription that paused a month simply has a shorter history.
    """
    rows = db.fetch_transactions(user_id, columns=_TXN_COLUMNS)
    history = [
        {"date": r["transaction_date"], "amount": float(r["amount"])}
        for r in rows
        if (r.get("transaction_type") or "").lower() == "expense"
        and (r.get("merchant") or "").strip().lower() == merchant.strip().lower()
    ]
    history.sort(key=lambda h: h["date"])
    return history


def _price_increase(history: list[dict]) -> tuple[dict, bool]:
    """Last stable-price change point in a chronological payment series.

    Returns (change, confirmed). ``confirmed`` means the new amount has been
    observed for at least two consecutive payments (or is the only payment),
    so month-to-month noise in utility bills never counts as a price change.
    """
    amounts = [h["amount"] for h in history]
    if not amounts:
        return {"previous_amount": None, "current_amount": None,
                "increase_amount": 0.0, "increase_percent": 0.0}, False
    current = amounts[-1]
    trailing = 0
    for a in reversed(amounts):
        if a == current:
            trailing += 1
        else:
            break
    change_idx = None
    for i in range(len(amounts) - 1, 0, -1):
        if amounts[i] != amounts[i - 1]:
            change_idx = i
            break
    if change_idx is None:
        return {"previous_amount": None, "current_amount": current,
                "increase_amount": 0.0, "increase_percent": 0.0}, True
    previous = amounts[change_idx - 1]
    increase = _f2(current - previous)
    percent = _f2((increase / previous * 100.0)) if previous > 0 else 0.0
    confirmed = trailing >= 2
    return {"previous_amount": previous, "current_amount": current,
            "increase_amount": increase, "increase_percent": percent}, confirmed


def detect(user_id: str) -> dict:
    """Scan recurring payments and report subscription signals (read-only)."""
    recurring = db.fetch_recurring(user_id, status="active")
    categories = categories_map()
    items: list[dict] = []

    for payment in recurring:
        merchant = str(payment.get("merchant") or "").strip()
        if not merchant:
            continue
        amount = float(payment.get("amount") or 0)
        frequency = str(payment.get("frequency") or "monthly").strip().lower()
        mult = _FREQ_MONTHLY_MULT.get(frequency, 1.0)
        monthly_cost = _f2(amount * mult)
        annual_cost = _f2(monthly_cost * 12.0)

        category_id = payment.get("category_id")
        category_name = str(categories.get(category_id, "")).strip() if category_id else ""
        category_key = category_name.strip().lower()

        history = _merchant_history(user_id, merchant)
        change, price_confirmed = _price_increase(history)
        increase_amount = change["increase_amount"]
        increase_percent = change["increase_percent"]
        current_amount = change["current_amount"] if change["current_amount"] is not None else amount
        # A price increase is only reported once it is CONFIRMED by history
        # (new amount paid at least twice); one-off fluctuations never count.
        if price_confirmed and change["previous_amount"] is not None and increase_amount > 0:
            prev_amount = change["previous_amount"]
        else:
            prev_amount = None
        annual_increase = _f2(increase_amount * mult * 12.0) if prev_amount is not None else 0.0

        latest = history[-1] if history else None
        previous_payment = history[-2] if len(history) >= 2 else None
        latest_amount = float(latest["amount"]) if latest else amount

        signals: list[str] = []
        if prev_amount is not None and increase_amount > 0:
            signals.append("PRICE_INCREASE")
        if annual_cost >= _HIGH_ANNUAL_THRESHOLD and category_key not in _ESSENTIAL_CATEGORIES:
            signals.append("HIGH_ANNUAL_COST")
        signals.append("RECURRING_COST")
        # de-duplicate while preserving the canonical signal order
        signals = [s for s in _SIGNAL_ORDER if s in signals]
        primary = signals[0] if signals else "RECURRING_COST"
        additional = signals[1:]

        is_essential = category_key in _ESSENTIAL_CATEGORIES
        if is_essential and primary != "PRICE_INCREASE":
            continue  # fixed commitments are fine unless their price changed

        item = {
            "merchant": merchant,
            "description": str(payment.get("description") or "").strip(),
            "frequency": frequency,
            "category": category_name,
            "monthly_cost": monthly_cost,
            "annual_cost": annual_cost,
            "previous_amount": prev_amount,
            "current_amount": current_amount,
            "increase_amount": increase_amount,
            "increase_percent": increase_percent,
            "annual_increase": annual_increase if prev_amount is not None else 0.0,
            "signal": primary,
            "additional_signals": additional,
            "latest_payment_date": latest["date"] if latest else None,
            "latest_payment_amount": latest_amount,
            "previous_payment_date": previous_payment["date"] if previous_payment else None,
            "previous_payment_amount": float(previous_payment["amount"]) if previous_payment else None,
            "payment_count": len(history),
            "evidence_refs": _evidence_refs(history, merchant, category_name),
        }
        items.append(item)

    # Price increases first, then by annual cost (desc).
    items.sort(key=lambda i: (i["signal"] != "PRICE_INCREASE", -i["annual_cost"]))

    recurring_monthly = _f2(sum(i["monthly_cost"] for i in items))
    changed = [i for i in items if i["signal"] == "PRICE_INCREASE"]
    return {
        "user_id": user_id,
        "items": items,
        "summary": {
            "changed_count": len(changed),
            "items_total": len(items),
            "recurring_monthly": recurring_monthly,
            "annualized_recurring_cost": _f2(recurring_monthly * 12.0),
            "signals": {
                "PRICE_INCREASE": len(changed),
                "RECURRING_COST": len(items),
                "HIGH_ANNUAL_COST": sum(1 for i in items if "HIGH_ANNUAL_COST" in i["additional_signals"]),
            },
        },
        "policy": {
            "executes": False,
            "cancels": False,
            "contacts": False,
            "mutations": [
                "action_drafts.status changes to approved/rejected ONLY on explicit user action",
            ],
        },
    }


def _evidence_refs(history: list[dict], merchant: str, category: str) -> list[str]:
    refs = [f"recurring_payments:{merchant}"]
    if category:
        refs.append(f"category:{category}")
    for h in history[-8:]:
        refs.append(f"txn:{h['date']}:{merchant}:{int(h['amount'])}")
    return refs


def _draft_text(item: dict) -> str:
    """Deterministic, fully-grounded draft description (never LLM prose)."""
    merchant = item["merchant"]
    if item["signal"] == "PRICE_INCREASE":
        prev = item["previous_amount"]
        cur = item["current_amount"]
        diff = item["increase_amount"]
        annual = item["annual_increase"]
        return (
            f"{merchant} increased from Rs {int(prev)}/month to Rs {int(cur)}/month. "
            f"That adds Rs {int(diff)}/month or approximately Rs {int(annual)}/year. "
            "Would you like to review whether this subscription is still worth keeping?"
        )
    return (
        f"{merchant} costs Rs {int(item['monthly_cost'])}/month "
        f"(Rs {int(item['annual_cost'])}/year). "
        "Review whether this recurring cost still makes sense for you."
    )


def create_draft(user_id: str, merchant: str) -> dict:
    """Create (idempotently) a review draft for one detected merchant."""
    data = detect(user_id)
    item = next((i for i in data["items"] if i["merchant"].strip().lower() == merchant.strip().lower()), None)
    if item is None:
        raise GuardianError(
            f"No guardian signal found for merchant: {merchant}. "
            "Only merchants flagged by subscription detection can be drafted."
        )

    if item["signal"] == "PRICE_INCREASE":
        title = f"Review {item['merchant']} price increase"
    else:
        title = f"Review {item['merchant']} subscription"
    description = _draft_text(item)

    # An approved or rejected action is NEVER re-proposed as a new draft.
    # The only way to get a fresh draft is to resolve-undo in the future;
    # until then the previous decision is returned unchanged.
    for existing in db.list_action_drafts(user_id):
        if existing.get("title") == title and existing.get("status") in ("approved", "rejected"):
            return {
                "action_id": existing["id"],
                "title": title,
                "description": description,
                "status": existing["status"],
                "merchant": item["merchant"],
                "signal": item["signal"],
                "previously_resolved": True,
            }

    payload = {
        "source": "guardian",
        "merchant": item["merchant"],
        "previous_amount": item["previous_amount"],
        "current_amount": item["current_amount"],
        "increase_amount": item["increase_amount"],
        "increase_percent": item["increase_percent"],
        "annual_increase": item["annual_increase"],
        "monthly_cost": item["monthly_cost"],
        "annual_cost": item["annual_cost"],
        "signal": item["signal"],
    }
    action_id = db.create_action_draft(
        user_id=user_id,
        action_type="review",
        title=title,
        description=description,
        payload=payload,
    )
    return {
        "action_id": action_id,
        "title": title,
        "description": description,
        "status": "draft",
        "merchant": item["merchant"],
        "signal": item["signal"],
    }


def summarize(user_id: str) -> dict:
    """Compact dashboard summary of guardian activity (read-only)."""
    data = detect(user_id)
    changed = next((i for i in data["items"] if i["signal"] == "PRICE_INCREASE"), None)
    summary = {"changed_count": data["summary"]["changed_count"], "items": []}
    if changed is not None:
        summary["items"].append({
            "merchant": changed["merchant"],
            "previous_amount": changed["previous_amount"],
            "current_amount": changed["current_amount"],
            "increase_amount": changed["increase_amount"],
            "annual_increase": changed["annual_increase"],
        })
    return summary