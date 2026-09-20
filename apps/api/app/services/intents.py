# NL intent router (Phase 4). Deterministic keyword/pattern matching.
#
# Selects TOOLS instead of guessing. Confidence is derived from how
# specific the matched pattern is.
from __future__ import annotations

import re

from app.services.analytics import categories_map

_INTENT_PATTERNS: list[tuple[str, re.Pattern, list[str]]] = [
    ("upcoming", re.compile(r"\b(upcoming|coming up|next payment|due soon|what.*pay)\b", re.I),
     ["get_upcoming_obligations", "get_recurring_payments"]),
    ("afford_purchase", re.compile(r"\b(can i afford|can we afford|should i (buy|get)|worth it|buy\b|purchase|laptop|iphone|bike|car|invest)\b", re.I),
     ["evaluate_affordability", "calculate_committed_budget", "get_financial_goals"]),
    ("rent_increase", re.compile(r"\brent\b.{0,20}increas|increas.{0,20}rent\b|\brent (goes up|hike)\b|\brent.*hike", re.I),
     ["get_monthly_summary", "simulate_expense_change", "calculate_committed_budget"]),
    ("guardian", re.compile(
        r"\bsubscription guardian\b|\bguard\b|\bprice (increase|hike)\b|"
        r"\bsubscriptions? (changed|change|increased|increase|hiked|raised|go(es|ing)? up|went up|gone up)\b|"
        r"\brecurring payments? (changed|change|increased|increase|hiked|raised|go(es|ing)? up|went up|gone up)\b|"
        r"\breview.*(subscription|recurring)|"
        r"\b(subscription|recurring).*worth (keeping|it)\b",
        re.I),
     ["guardian_detect", "get_recurring_payments", "get_monthly_summary"]),
    ("what_changed", re.compile(r"\b(changed|change|increased|increases|increase|compare|compared|versus|vs\b|last month|month over month|different|trend|go up|gone up|went up)\b", re.I),
     ["compare_periods", "get_monthly_summary", "detect_anomalies"]),
    ("committed", re.compile(r"\b(committed|already (tied|allocated|committed)|obligation|locked in|fixed (cost|expense))\b", re.I),
     ["calculate_committed_budget", "get_recurring_payments"]),
    ("goal_save", re.compile(r"\b(save each month|monthly saving|need to save|reach my (goal|target)|toward my goal|for my (goal|target))\b", re.I),
     ["simulate_goal", "get_financial_goals"]),
    ("goal_track", re.compile(r"\b(on track|am i on track|goal progress|emergency fund|progress.*goal|how.*doing.*goal)\b", re.I),
     ["get_financial_goals", "get_monthly_summary"]),
    ("subscriptions", re.compile(r"\b(subscription|subscriptions|recurring|netflix|spotify|emi\b|paying for|membership)\b", re.I),
     ["get_recurring_payments"]),
    ("anomaly", re.compile(r"\b(unusual|abnormal|anomal|anomaly|spike|why.*(high|much)|double charged|duplicate)\b", re.I),
     ["detect_anomalies", "get_monthly_summary"]),
    ("category_amount", re.compile(r"\b(how much.*(spend|spent|on)|spent on|spending on)\b", re.I),
     ["get_category_breakdown", "get_transactions"]),
    ("spend_most", re.compile(r"\b(where did i spend|spend the most|most this month|where.*my money|biggest (spend|expense)|top (category|spend)|went to)\b", re.I),
     ["get_category_breakdown", "get_monthly_summary"]),
    ("overview", re.compile(r"\b(money|finances|summary|this month|status|report|how am i doing|overview)\b", re.I),
     ["get_monthly_summary", "get_category_breakdown", "detect_anomalies"]),
]

_DEFAULT_INTENT = "overview"
_DEFAULT_TOOLS = ["get_monthly_summary", "get_category_breakdown", "detect_anomalies"]


def _category_hit(question: str) -> str | None:
    """Return a category name mentioned in the question (exact substring)."""
    lowered = question.lower()
    for name in categories_map().values():
        if name.lower() in lowered:
            return name
    return None


def classify(question: str) -> dict:
    """Return {'intent': str, 'pattern': str, 'confidence': float, 'tools': [...]}."""
    question = (question or "").strip()
    for name, pattern, tools in _INTENT_PATTERNS:
        if pattern.search(question):
            # "category_amount" needs an actual category word to be high-confidence
            confidence = 1.0
            if name == "category_amount":
                confidence = 0.85 if _category_hit(question) else 0.5
            return {"intent": name, "pattern": pattern.pattern,
                    "confidence": round(confidence, 2), "tools": list(tools)}
    return {"intent": _DEFAULT_INTENT, "pattern": "fallback",
            "confidence": 0.4, "tools": list(_DEFAULT_TOOLS)}


def plan_tools(question: str) -> dict:
    info = classify(question)
    return info


def intent_label(intent: str) -> str:
    return {
        "spend_most": "spending analysis",
        "category_amount": "category analysis",
        "subscriptions": "recurring analysis",
        "what_changed": "month-over-month comparison",
        "afford_purchase": "affordability simulation",
        "committed": "commitment analysis",
        "goal_save": "goal saving plan",
        "rent_increase": "rent increase simulation",
        "upcoming": "upcoming obligations",
        "goal_track": "goal progress",
        "anomaly": "anomaly detection",
        "guardian": "subscription guardian",
        "overview": "monthly overview",
    }.get(intent, intent)