# Financial goal intelligence (Phase 4). Deterministic, evidence-grounded.
from __future__ import annotations

import math
from datetime import date

from app import db


def _f2(v: float) -> float:
    return round(float(v), 2)


def _months_between(a: date, b: date) -> int:
    return max(0, (b.year - a.year) * 12 + (b.month - a.month))


def goal_analysis(user_id: str) -> dict:
    goals = []
    for g in db.fetch_goals(user_id):
        target = float(g["target_amount"]) or 0.0
        current = float(g["current_amount"]) or 0.0
        remaining = max(0.0, target - current)
        progress = (current / target * 100.0) if target > 0 else 0.0
        required_monthly = None
        months_to_target = None
        target_date = g.get("target_date")
        if target_date:
            try:
                td = date.fromisoformat(target_date)
                months_to_target = _months_between(date.today(), td)
                if months_to_target > 0 and remaining > 0:
                    required_monthly = _f2(remaining / months_to_target)
            except ValueError:
                pass
        goals.append({
            "id": g["id"], "name": g["name"],
            "target_amount": _f2(target), "current_amount": _f2(current),
            "remaining": _f2(remaining), "progress_pct": _f2(progress),
            "target_date": target_date, "priority": g.get("priority", 3),
            "status": g.get("status", "in_progress"),
            "months_to_target": months_to_target,
            "required_monthly": required_monthly,
        })
    return {"goals": goals, "count": len(goals)}


def primary_goal(user_id: str) -> dict | None:
    """Deterministic goal selection: lowest priority number, then first."""
    goals = goal_analysis(user_id)["goals"]
    if not goals:
        return None
    return goals[0]


def months_to_complete(remaining: float, monthly_savings: float) -> int | None:
    if monthly_savings <= 0:
        return None
    return math.ceil(remaining / monthly_savings)


def goal_impact(user_id: str, monthly_savings: float,
                delta_monthly: float = 0.0, one_time: float = 0.0) -> dict:
    """Impact of a spending/saving change on the primary goal.

    one_time > 0  -> a one-time purchase reduces current savings balance.
    delta_monthly -> sustained monthly change to savings (can be negative).
    """
    goal = primary_goal(user_id)
    if goal is None:
        return {"goal": None, "months_baseline": None, "months_scenario": None,
                "delay_months": None, "impact": None}
    baseline_savings = monthly_savings
    scenario_savings = monthly_savings + delta_monthly
    remaining = goal["remaining"]
    remaining_scenario = max(0.0, remaining + one_time)

    m_base = months_to_complete(remaining, baseline_savings)
    m_scen = months_to_complete(remaining_scenario, scenario_savings)
    delay = None
    if m_base is not None and m_scen is not None:
        delay = m_scen - m_base

    return {
        "goal": goal["name"],
        "goal_id": goal["id"],
        "target_amount": goal["target_amount"],
        "current_amount": goal["current_amount"],
        "remaining": _f2(remaining),
        "progress_pct": goal["progress_pct"],
        "months_baseline": m_base,
        "months_scenario": m_scen,
        "delay_months": delay,
        "impact": ("delayed" if (delay or 0) > 0
                   else ("accelerated" if (delay or 0) < 0 else "unchanged")),
    }