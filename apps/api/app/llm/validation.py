# Validation layer for LLM output (Phase 5).
#
# The LLM is untrusted: we validate every structured response against a strict
# allowlist before it can influence execution or the answer. Unknown intents,
# unknown tools, unknown arguments, malformed argument types and prompt
# injections are all rejected here.
from __future__ import annotations

import json
import re
from typing import Any

from app.llm.schemas import LLMAnswerOut, LLMIntentOut, LLMToolPlan

# The only intents the LLM may return (mirror of the deterministic router).
VALID_INTENTS = frozenset({
    "overview", "spend_most", "category_amount", "subscriptions", "what_changed",
    "afford_purchase", "rent_increase", "committed", "goal_save", "goal_track",
    "upcoming", "anomaly",
})

MAX_ANSWER_CHARS = 2000
MAX_TOOLS_PER_PLAN = 8
MAX_TOTAL_ARGS = 8
MAX_AMOUNT = 1_000_000  # INR, "reasonable maximum" guard for financial args

# Allowlisted argument keys per tool. The LLM may only propose these keys.
TOOL_ALLOWED_ARGS: dict[str, frozenset[str]] = {
    "get_transactions": frozenset({"start_date", "end_date", "limit"}),
    "get_monthly_summary": frozenset({"year", "month"}),
    "get_category_breakdown": frozenset({"year", "month", "start_date", "end_date"}),
    "get_recurring_payments": frozenset(),
    "get_financial_goals": frozenset(),
    "get_budget_status": frozenset({"year", "month"}),
    "compare_periods": frozenset({"year", "month"}),
    "detect_anomalies": frozenset({"year", "month"}),
    "simulate_goal": frozenset(),
    "simulate_expense_change": frozenset({"amount"}),
    "calculate_committed_budget": frozenset({"year", "month"}),
    "get_upcoming_obligations": frozenset({"days"}),
    "evaluate_affordability": frozenset({"amount"}),
}


def _scalar_jsonable(value: Any) -> bool:
    """Arguments must be plain JSON scalars (no nested objects/arrays)."""
    return value is None or isinstance(value, (str, int, float, bool))


def _arg_valid(tool_name: str, key: str, value: Any) -> bool:
    """Type/range validation for each allowlisted argument."""
    if tool_name == "get_transactions":
        if key == "limit":
            return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 1000
        if key in ("start_date", "end_date"):
            return isinstance(value, str) and 10 <= len(value) <= 10
    if tool_name in ("get_monthly_summary", "get_category_breakdown", "compare_periods",
                     "detect_anomalies", "get_budget_status", "calculate_committed_budget"):
        if key in ("year", "month"):
            if key == "year":
                return isinstance(value, int) and not isinstance(value, bool) and 2020 <= value <= 2100
            return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 12
        if key in ("start_date", "end_date"):
            return isinstance(value, str) and 10 <= len(value) <= 10
    if tool_name == "simulate_expense_change":
        if key == "amount":
            return (isinstance(value, (int, float)) and not isinstance(value, bool)
                    and 0 < float(value) <= MAX_AMOUNT)
    if tool_name == "evaluate_affordability":
        if key == "amount":
            return (isinstance(value, (int, float)) and not isinstance(value, bool)
                    and 0 < float(value) <= MAX_AMOUNT)
    if tool_name == "get_upcoming_obligations":
        if key == "days":
            return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 365
    return False


def extract_json_text(text: str) -> str:
    """Pull the outermost JSON object out of free-form LLM text."""
    if not text:
        return ""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return ""
    return text[start:end + 1]


def _loads(data: Any) -> dict | None:
    """Robust JSON parse: accepts a dict already, or a JSON string (with or
    without code fences / prose). Returns None on failure."""
    if isinstance(data, dict):
        return data
    if not isinstance(data, str):
        return None
    extracted = extract_json_text(data)
    if not extracted:
        return None
    try:
        parsed = json.loads(extracted)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def validate_intent(data: Any) -> LLMIntentOut | None:
    """Return a validated LLMIntentOut, or None if the LLM output is unusable."""
    payload = _loads(data)
    if payload is None:
        return None
    intent = payload.get("intent")
    if not isinstance(intent, str) or intent not in VALID_INTENTS:
        return None
    try:
        return LLMIntentOut(
            intent=intent,
            reason=str(payload.get("reason", ""))[:200],
            confidence=float(payload.get("confidence", 0.0)),
        )
    except (TypeError, ValueError):
        return None


def validate_tool_plan(data: Any) -> LLMToolPlan | None:
    """Validate an LLM tool plan against the registry allowlist.

    Rejects: unknown intents, unknown tools, unknown argument keys,
    non-scalar or wrongly typed arguments, oversized plans.
    """
    payload = _loads(data)
    if payload is None:
        return None
    intent = payload.get("intent")
    if not isinstance(intent, str) or intent not in VALID_INTENTS:
        return None
    raw_tools = payload.get("tools")
    if not isinstance(raw_tools, list) or not raw_tools:
        return None
    if len(raw_tools) > MAX_TOOLS_PER_PLAN:
        return None

    from app.services.tools import TOOLS  # registry is the source of truth

    tools = []
    for item in raw_tools:
        if not isinstance(item, dict):
            return None
        name = item.get("name")
        arguments = item.get("arguments")
        if not isinstance(name, str) or name not in TOOLS:
            return None
        if name not in TOOL_ALLOWED_ARGS:
            return None
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict) or len(arguments) > MAX_TOTAL_ARGS:
            return None
        for key, value in arguments.items():
            if key not in TOOL_ALLOWED_ARGS[name]:
                return None
            if not _scalar_jsonable(value) or not _arg_valid(name, key, value):
                return None
        tools.append({"name": name, "arguments": dict(arguments)})
    try:
        return LLMToolPlan(intent=intent,
                           reason=str(payload.get("reason", ""))[:200],
                           tools=tools)
    except (TypeError, ValueError):
        return None


def validate_answer(data: Any) -> LLMAnswerOut | None:
    """Validate the final natural-language answer draft."""
    payload = _loads(data)
    if payload is None:
        return None
    answer = payload.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return None
    answer = answer.strip()
    if len(answer) > MAX_ANSWER_CHARS:
        answer = answer[:MAX_ANSWER_CHARS]
    warnings = payload.get("warnings", []) or []
    refs = payload.get("evidence_refs", []) or []
    try:
        return LLMAnswerOut(
            answer=answer,
            warnings=[str(w)[:200] for w in warnings],
            uncertainty=(str(payload["uncertainty"])[:200]
                         if payload.get("uncertainty") else None),
            evidence_refs=[str(r)[:200] for r in refs],
        )
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Evidence grounding check.
# ---------------------------------------------------------------------------
_NUMBER_TOKEN = re.compile(r"\d{1,3}(?:,\d{3})+|\d{3,}(?:\.\d+)?")


def _is_year(bare: str) -> bool:
    """4-digit years (2020-2100) are calendar references, not financial figures."""
    return len(bare) == 4 and 2020 <= int(bare) <= 2100


def is_ungrounded(answer: str, context: str) -> bool:
    """True if the answer cites a figure that does NOT appear in the evidence.

    Only figures of 3+ digits are checked (counts like '12 payments', '3
    anomalies' are typically smaller and not treated as financial evidence).
    Calendar years are exempt. Commas and the rupee sign are normalized on
    both sides.
    """
    if not answer or not context:
        return True
    ctx = re.sub(r"[₹,]|,\s", "", context)
    for match in _NUMBER_TOKEN.finditer(answer):
        bare = match.group(0).replace(",", "")
        if len(bare) >= 4 and not _is_year(bare):  # amounts >= 1,000
            if bare not in ctx:
                return True
    return False