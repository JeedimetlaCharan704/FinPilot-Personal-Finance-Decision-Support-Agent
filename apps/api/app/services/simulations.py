# Decision simulation engine (Phase 4) - the flagship feature.
#
# NEVER touches real transactions. Produces hypothetical baseline vs scenario
# projections with explicit assumptions. Decision-support only.
from __future__ import annotations

import math

from app import db
from app.services import analytics, goals


def _f2(v: float) -> float:
    return round(float(v), 2)


def _inr(v: float) -> str:
    return f"\u20b9{v:,.0f}"


def _snapshot(income: float, expenses: float, committed: float) -> dict:
    net = income - expenses
    savings_rate = (net / income * 100.0) if income > 0 else 0.0
    return {
        "label": "projection",
        "monthly_income": _f2(income),
        "monthly_expenses": _f2(expenses),
        "monthly_savings": _f2(net),
        "savings_rate": _f2(savings_rate),
        "committed": _f2(committed),
    }


def run_simulation(user_id: str, scenario_type: str, name: str, amount: float,
                   frequency: str = "one_time", duration_months: int = 1,
                   reference_id: str = "") -> dict:
    """Deterministic hypothetical scenario engine.

    scenario_type:
      purchase            -> one-time outflow (e.g. buy a laptop)
      monthly_spend       -> sustained monthly expense increase
      rent_increase       -> sustained monthly expense increase (named)
      extra_savings       -> sustained monthly saving increase
      cancel_subscription -> frees a recurring payment amount monthly
    """
    summary = analytics.monthly_summary(user_id)
    base = _snapshot(summary["income"], summary["expenses"], summary["committed"])
    month_label = summary.get("period_label", "latest month")
    monthly_savings = base["monthly_savings"]

    if not summary.get("has_data", False):
        return {"error": "no_data",
                "explanation": "No transaction data available for simulation.",
                "assumptions": [], "baseline": base, "scenario": base,
                "difference": {}, "goal_impact": {}}

    label = (name or scenario_type.replace("_", " ")).title()
    delta_monthly = 0.0      # sustained change to monthly savings
    one_time = 0.0           # one-time outflow
    annualized_effect = 0.0
    assumptions = [
        f"Baseline uses the latest data month: {month_label}.",
        "No real transactions are changed; this is a hypothetical scenario.",
        "Monthly savings stay constant at the baseline value unless changed by the scenario.",
        "This is an informational analysis, not financial advice.",
    ]

    if scenario_type in ("monthly_spend", "rent_increase"):
        delta_monthly = -amount
        # per-year cost if the change is sustained for a full year
        annualized_effect = -amount * 12
        label = f"Rent increase" if scenario_type == "rent_increase" else "Monthly spend increase"
        assumptions.append(
            f"{label}: monthly spending rises by {_inr(amount)} for "
            f"{duration_months} month(s), reducing monthly savings by the same amount.")
        if scenario_type == "rent_increase":
            label = f"{label} +{_inr(amount)}"

    elif scenario_type == "purchase":
        one_time = amount
        label = name or "One-time purchase"
        assumptions.append(
            f"One-time outflow of {_inr(amount)} is funded from cash, reducing "
            "your emergency-fund balance by that amount immediately.")

    elif scenario_type == "extra_savings":
        delta_monthly = amount
        annualized_effect = amount * 12
        label = "Extra monthly savings"
        assumptions.append(
            f"You additionally save {_inr(amount)} per month (sustained).")

    elif scenario_type == "cancel_subscription":
        recurring = {r["id"]: r for r in db.fetch_recurring(user_id)}
        ref = recurring.get(reference_id)
        if ref is None and recurring:
            ref = next(iter(recurring.values()))  # deterministic fallback: largest
        if ref:
            freed = float(ref["amount"]) * analytics.FREQ_MONTHLY_MULT.get(ref["frequency"], 1.0)
            delta_monthly = freed
            annualized_effect = freed * 12
            label = f"Cancel {ref['merchant']}"
            assumptions.append(
                f"Cancelling {ref['merchant']} frees {_inr(freed)} per month "
                f"(current amount {_inr(float(ref['amount']))}, "
                f"{ref['frequency']} frequency, annualized {_inr(freed * 12)}).")
        else:
            assumptions.append("No recurring payment found to cancel; scenario is a no-op.")

    # delta_monthly is the CHANGE in savings, so scenario expenses move the
    # opposite way: expenses_scenario = expenses - delta_monthly.
    scenario = _snapshot(
        summary["income"],
        _f2(summary["expenses"] - delta_monthly),
        summary["committed"],
    )
    scenario["label"] = label

    cumulative_over_duration = one_time + delta_monthly * duration_months
    difference = {
        "monthly_savings": _f2(scenario["monthly_savings"] - base["monthly_savings"]),
        "annualized": _f2(annualized_effect),
        "one_time": _f2(one_time),
        "duration_months": int(duration_months),
        "total_cumulative": _f2(cumulative_over_duration),
    }

    gi = goals.goal_impact(user_id, monthly_savings=monthly_savings,
                           delta_monthly=delta_monthly, one_time=one_time)

    explanation = _explain(scenario_type, summary, base, scenario, gi, one_time,
                           delta_monthly, month_label)

    return {
        "scenario_type": scenario_type,
        "baseline": base,
        "scenario": scenario,
        "difference": difference,
        "goal_impact": gi,
        "explanation": explanation,
        "assumptions": assumptions,
    }


def _explain(scenario_type, summary, base, scenario, gi, one_time, delta_monthly,
             month_label) -> str:
    parts = [
        f"Baseline ({month_label}): you save about {_inr(base['monthly_savings'])} per month "
        f"(income {_inr(base['monthly_income'])}, expenses {_inr(base['monthly_expenses'])})."
    ]
    if scenario_type == "purchase":
        parts.append(
            f"Under the selected assumptions, this {_inr(one_time)} purchase would reduce "
            "your emergency-fund progress by the full amount immediately.")
        if gi.get("delay_months") is not None:
            if gi["delay_months"] > 0:
                parts.append(f"That delays completing your '{gi['goal']}' goal by about "
                             f"{gi['delay_months']} month(s) at your current saving pace.")
            else:
                parts.append(f"Your '{gi['goal']}' goal timeline is unchanged on a "
                             "monthly-savings basis.")
        elif gi.get("months_baseline") is None:
            parts.append("You are currently not saving a positive amount, so no "
                         "completion timeline can be projected.")
    elif scenario_type in ("monthly_spend", "rent_increase"):
        parts.append(
            f"This change lowers your monthly savings to {_inr(scenario['monthly_savings'])}.")
        if gi.get("delay_months"):
            parts.append(f"It would delay your '{gi['goal']}' goal by about "
                         f"{gi['delay_months']} month(s).")
    elif scenario_type == "extra_savings":
        parts.append(f"Saving {_inr(delta_monthly)} extra per month raises monthly savings "
                     f"to {_inr(scenario['monthly_savings'])}.")
        if gi.get("delay_months") is not None and gi["delay_months"] < 0:
            parts.append(f"It would reach your '{gi['goal']}' goal about "
                         f"{-gi['delay_months']} month(s) sooner.")
    elif scenario_type == "cancel_subscription":
        parts.append(f"Cancelling frees {_inr(delta_monthly)} per month, raising monthly "
                     f"savings to {_inr(scenario['monthly_savings'])}.")
        if gi.get("delay_months") is not None and gi["delay_months"] < 0:
            parts.append(f"Your '{gi['goal']}' goal would complete about "
                         f"{-gi['delay_months']} month(s) sooner.")
    return " ".join(parts)