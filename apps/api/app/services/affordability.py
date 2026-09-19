# Affordability decision engine (Phase 6) — the hero "Can I afford this?" flow.
#
# Everything here is deterministic and sourced from the existing analytics /
# goals / simulations engines. No LLM computes numbers. No new financial
# engine: we compose existing primitives (monthly_summary, budget_status,
# goal_analysis, goal_impact, months_to_complete) into a structured decision.
from __future__ import annotations

import math
import re

from app.services import analytics, goals

# Mirror of llm.validation.MAX_AMOUNT: the "reasonable maximum" for a purchase.
MAX_PURCHASE_AMOUNT = 1_000_000

# ---------------------------------------------------------------------------
# Safe deterministic INR amount parsing (STEP 4).
# ---------------------------------------------------------------------------
# Supported forms (case-insensitive):
#   "₹65,000" "₹65000" "65,000" "65000" "65k" "₹65k"
#   "₹20k" "60,000 rupee laptop" "50000 phone" "20000 inr"
_NUMBER = r"\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?"
_TOKEN_RE = re.compile(
    r"(?:₹|rs\.?|inr|rupees?)\s*(" + _NUMBER + r")\s*(k|thousand)?"
    r"|(" + _NUMBER + r")\s*(k|thousand)?\s*(₹|rs\.?|inr|rupees?)?",
    re.IGNORECASE,
)


def _is_year(bare_digits: str) -> bool:
    """4-digit calendar years (2020-2100) are never purchase amounts."""
    if len(bare_digits) == 4 and bare_digits.isdigit():
        v = int(bare_digits)
        return 2020 <= v <= 2100
    return False


def parse_purchase_amount(question: str | None) -> float | None:
    """Extract a purchase amount in INR from natural language.

    Deterministic rules (documented):
      1. Every numeric token is considered, with an optional currency marker
         (₹, rs, inr, rupees) and optional k/thousand multiplier.
      2. Tokens are ranked: explicit currency prefix > k/thousand suffix >
         trailing currency word > bare number. Within a tier the largest
         amount wins.
      3. Bare 4-digit calendar years (2020-2100) are ignored.
      4. Values outside 1..MAX_PURCHASE_AMOUNT are rejected (returns None).
    Returns the amount as a float, or None when no valid amount is found.
    """
    text = (question or "").strip()
    if not text:
        return None
    candidates: list[tuple[int, float, str]] = []  # (tier, amount, source)
    for match in _TOKEN_RE.finditer(text):
        num_str = match.group(1) or match.group(3)
        if not num_str:
            continue
        # A leading minus means the amount is negative, not a purchase figure.
        if match.start() > 0 and text[match.start() - 1] in "-−":
            continue
        suffix = (match.group(2) or match.group(4) or "").lower()
        trailing = match.group(5) or ""
        bare = num_str.replace(",", "")
        if _is_year(bare):
            continue
        amount = float(bare)
        if suffix in ("k", "thousand"):
            amount *= 1000.0
        if trailing in ("rs", "rs.", "inr", "rupee", "rupees"):
            suffix = "word"  # trailing currency word ranks above bare numbers
        if match.group(1) is not None:  # explicit currency prefix (highest)
            tier = 3
        elif suffix in ("k", "thousand"):
            tier = 2
        elif suffix == "word":
            tier = 2
        else:
            tier = 1
        candidates.append((tier, amount, match.group(0)))

    if not candidates:
        return None
    # Highest tier wins; ties resolved by the largest amount.
    best_tier = max(c[0] for c in candidates)
    top = [c for c in candidates if c[0] == best_tier]
    amount = max(c[1] for c in top)
    if not (1.0 <= amount <= MAX_PURCHASE_AMOUNT):
        return None
    return round(amount, 2)


def validate_purchase_amount(value) -> float:
    """Strict guard used by the tool registry (raises on unsafe values)."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        raise ValueError("Purchase amount must be a number") from None
    if not (1.0 <= amount <= MAX_PURCHASE_AMOUNT):
        raise ValueError(
            f"Purchase amount must be between 1 and "
            f"{MAX_PURCHASE_AMOUNT:,.0f} INR")
    return round(amount, 2)


# ---------------------------------------------------------------------------
# The decision engine (STEP 2/3/5/6).
# ---------------------------------------------------------------------------
def _delay(remaining: float, free_cash: float,
           extra_outflow: float = 0.0, extra_saving: float = 0.0) -> int | None:
    """Primary-goal delay (months) after an outflow, offset by optional saving."""
    m_base = goals.months_to_complete(remaining, free_cash)
    if m_base is None:
        return None
    m_scn = goals.months_to_complete(
        max(0.0, remaining + extra_outflow - extra_saving), free_cash)
    if m_scn is None:
        return None
    return m_scn - m_base


def _goal_impacts(user_id: str, amount: float, free_cash: float) -> list[dict]:
    """Per-goal deterministic impact of a one-time purchase.

    Uses the existing goals.months_to_complete helper for every goal
    (the primary-goal function goals.goal_impact is used for scenarios).
    """
    out: list[dict] = []
    for g in goals.goal_analysis(user_id)["goals"]:
        remaining = float(g["remaining"])
        m_base = goals.months_to_complete(remaining, free_cash)
        m_after = goals.months_to_complete(remaining + amount, free_cash)
        delay = None
        if m_base is not None and m_after is not None:
            delay = m_after - m_base
        impact = ("delayed" if (delay or 0) > 0
                  else ("accelerated" if (delay or 0) < 0 else "unchanged"))
        # Required monthly saving to stay on the stated target date.
        req_base = g.get("required_monthly")
        months_left = g.get("months_to_target")
        req_after = None
        if months_left and months_left > 0:
            req_after = round((remaining + amount) / months_left, 2)
        out.append({
            "goal": g["name"],
            "goal_id": g["id"],
            "target_amount": float(g["target_amount"]),
            "remaining": remaining,
            "progress_pct": float(g["progress_pct"]),
            "months_baseline": m_base,
            "months_after_purchase": m_after,
            "delay_months": delay,
            "impact": impact,
            "required_monthly_baseline": req_base,
            "required_monthly_scenario": req_after,
        })
    return out


def _scenarios(user_id: str, amount: float, free_cash: float,
               cash_after: float, months_to_save: int | None) -> list[dict]:
    """Useful alternatives, every number deterministic (STEP 5)."""
    out: list[dict] = []
    goals_list = goals.goal_analysis(user_id)["goals"]
    remaining = float(goals_list[0]["remaining"]) if goals_list else 0.0

    # A — Buy now (fund from one month's free cash flow).
    out.append({
        "label": "Buy now",
        "amount": amount,
        "cash_after_purchase": round(cash_after, 2),
        "months_to_save": None,
        "goal_delay_months": _delay(remaining, free_cash, extra_outflow=amount),
        "detail": "Fund the full amount from this month's free cash flow.",
    })

    # B — Save N months, then buy.
    if months_to_save and free_cash > 0:
        accumulated = round(months_to_save * free_cash, 2)
        out.append({
            "label": f"Save {months_to_save} month"
                     f"{'s' if months_to_save > 1 else ''}, then buy",
            "amount": amount,
            "cash_after_purchase": round(accumulated - amount, 2),
            "months_to_save": months_to_save,
            "goal_delay_months": _delay(
                remaining, free_cash, extra_outflow=amount,
                extra_saving=accumulated),
            "detail": (f"Set aside {_inr(free_cash)}/month for "
                       f"{months_to_save} month(s) — {_inr(accumulated)} "
                       f"accumulated before buying."),
        })

    # C — Trim discretionary spending to buy next month.
    trim = round(max(0.0, amount - free_cash), 2)
    if trim > 0:
        out.append({
            "label": "Trim discretionary spending",
            "amount": amount,
            "cash_after_purchase": 0.0,
            "months_to_save": 1,
            # free cash + trim fully covers the purchase -> balance unchanged.
            "goal_delay_months": _delay(remaining, free_cash,
                                        extra_outflow=amount,
                                        extra_saving=amount),
            "detail": (f"Cut {_inr(trim)}/month of discretionary spending "
                       f"for one month so free cash covers the purchase."),
        })

    # D — Smaller purchase that fits this month's free cash.
    afford_now = round(max(0.0, free_cash), 2)
    if afford_now > 0 and afford_now < amount:
        out.append({
            "label": "Smaller purchase",
            "amount": afford_now,
            "cash_after_purchase": 0.0,
            "months_to_save": None,
            "goal_delay_months": _delay(remaining, free_cash,
                                        extra_outflow=afford_now),
            "detail": (f"A one-time purchase of {_inr(afford_now)} fits "
                       f"within this month's free cash flow (₹0 left over)."),
        })
    return out


def evaluate_affordability(user_id: str, amount: float,
                           year: int | None = None,
                           month: int | None = None) -> dict:
    """Deterministic affordability decision for a one-time purchase.

    Verdict rules (documented):
      INSUFFICIENT_DATA  -> no transaction data (or unsafe amount).
      AFFORDABLE         -> amount <= free cash flow (this month's net).
      TIGHT              -> free cash < amount <= 2 x free cash.
      NOT_YET            -> amount > 2 x free cash (or no positive free cash).

    free cash flow = income - actual spending (analytics.net).
    committed_outflows = active recurring commitments/month.
    normal discretionary spend = spending beyond those commitments.
    Therefore: income = committed + normal discretionary + free cash.
    """
    try:
        amount = validate_purchase_amount(amount)
    except ValueError as exc:
        return {
            "has_data": False, "verdict": "INSUFFICIENT_DATA",
            "purchase_amount": _num(_safe_amount(amount)),
            "projected_income": 0.0, "committed_outflows": 0.0,
            "normal_discretionary_spend": 0.0, "free_cash": 0.0,
            "cash_after_purchase": 0.0, "months_to_save": None,
            "goal_impacts": [], "scenarios": [],
            "assumptions": [], "warnings": [str(exc)],
        }

    summary = analytics.monthly_summary(user_id, year, month)
    budget = analytics.budget_status(user_id, year, month)
    if not summary.get("has_data", False):
        return {
            "has_data": False, "verdict": "INSUFFICIENT_DATA",
            "purchase_amount": amount,
            "projected_income": 0.0, "committed_outflows": 0.0,
            "normal_discretionary_spend": 0.0, "free_cash": 0.0,
            "cash_after_purchase": round(-amount, 2), "months_to_save": None,
            "goal_impacts": [], "scenarios": [],
            "assumptions": [
                "No transaction data is available to assess this purchase.",
            ],
            "warnings": [],
        }

    income = _num(summary["income"])
    committed = _num(budget.get("committed") or summary.get("committed") or 0.0)
    spent = _num(summary["expenses"])
    free_cash = _num(summary["net"])  # income - actual spending
    normal_discretionary = _num(max(0.0, spent - committed))
    cash_after = _num(free_cash - amount)
    months_to_save = (math.ceil(amount / free_cash)
                      if free_cash > 0 else None)

    if free_cash <= 0 or amount > 2 * free_cash:
        verdict = "NOT_YET"
    elif amount <= free_cash:
        verdict = "AFFORDABLE"
    else:
        verdict = "TIGHT"

    impacts = _goal_impacts(user_id, amount, free_cash)
    scenarios = _scenarios(user_id, amount, free_cash, cash_after,
                           months_to_save)

    assumptions = [
        "Free cash flow = latest month's income minus actual spending (net cash flow).",
        "Committed outflows = active recurring payments expressed per month.",
        "Normal discretionary spend = actual spending beyond recurring commitments.",
        f"Verdict thresholds: affordable at or under one month's free cash flow, "
        f"tight up to twice that, otherwise not yet.",
        "A one-time purchase is assumed to be funded from cash, reducing goal balances immediately.",
        "This is an informational, decision-support analysis — not financial advice.",
    ]

    return {
        "has_data": True,
        "verdict": verdict,
        "purchase_amount": amount,
        "projected_income": income,
        "committed_outflows": committed,
        "normal_discretionary_spend": normal_discretionary,
        "free_cash": free_cash,
        "cash_after_purchase": cash_after,
        "months_to_save": months_to_save,
        "goal_impacts": impacts,
        "scenarios": scenarios,
        "assumptions": assumptions,
        "warnings": [],
        "period": summary.get("period_label", ""),
    }


def _safe_amount(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _num(v) -> float:
    return round(float(v), 2)


def _inr(v: float) -> str:
    return f"\u20b9{v:,.0f}"