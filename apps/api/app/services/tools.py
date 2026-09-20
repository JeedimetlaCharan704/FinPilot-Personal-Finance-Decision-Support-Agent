# Internal tool system (Phase 4).
#
# Every tool: validates input, queries Supabase efficiently (SQL-filtered
# reads / pre-aggregated data), returns structured deterministic output.
from __future__ import annotations

from app import db
from app.services import affordability, analytics, anomalies, goals, guardian, simulations


class ToolValidationError(ValueError):
    """Raised when tool input is invalid."""


def _require(args: dict, *keys: str) -> None:
    for key in keys:
        if args.get(key) in (None, ""):
            raise ToolValidationError(f"Missing required tool argument: {key}")


def _get_transactions(user_id: str, args: dict) -> dict:
    start = args.get("start_date")
    end = args.get("end_date")
    limit = args.get("limit")
    rows = db.fetch_transactions(user_id, start_date=start, end_date=end,
                                 limit=limit or 100,
                                 columns="id,category_id,transaction_date,amount,transaction_type,description,merchant")
    cmap = analytics.categories_map()
    out = []
    for t in rows:
        out.append({
            "id": t["id"], "date": t["transaction_date"],
            "category": cmap.get(t.get("category_id"), "Other"),
            "amount": float(t["amount"]), "type": t["transaction_type"],
            "merchant": t.get("merchant", ""), "description": t.get("description", ""),
        })
    return {"transactions": out, "count": len(out)}


def _get_monthly_summary(user_id: str, args: dict) -> dict:
    return analytics.monthly_summary(user_id, args.get("year"), args.get("month"))


def _get_category_breakdown(user_id: str, args: dict) -> dict:
    return analytics.category_breakdown(user_id,
                                        start_date=args.get("start_date"),
                                        end_date=args.get("end_date"),
                                        year=args.get("year"), month=args.get("month"))


def _get_recurring_payments(user_id: str, args: dict) -> dict:
    return analytics.recurring_analysis(user_id)


def _get_financial_goals(user_id: str, args: dict) -> dict:
    return goals.goal_analysis(user_id)


def _get_budget_status(user_id: str, args: dict) -> dict:
    return analytics.budget_status(user_id, args.get("year"), args.get("month"))


def _compare_periods(user_id: str, args: dict) -> dict:
    return analytics.compare_periods(user_id, args.get("year"), args.get("month"))


def _detect_anomalies(user_id: str, args: dict) -> dict:
    return anomalies.detect_anomalies(user_id, args.get("year"), args.get("month"))


def _simulate_goal(user_id: str, args: dict) -> dict:
    return goals.goal_analysis(user_id)


def _simulate_expense_change(user_id: str, args: dict) -> dict:
    amount = args.get("amount")
    if amount is None:
        raise ToolValidationError("simulate_expense_change requires 'amount'")
    summary = analytics.monthly_summary(user_id)
    gi = goals.goal_impact(user_id, monthly_savings=summary["net"],
                           delta_monthly=-float(amount))
    return {"monthly_savings": summary["net"],
            "projected_monthly_savings": round(summary["net"] - float(amount), 2),
            "goal_impact": gi}


def _calculate_committed_budget(user_id: str, args: dict) -> dict:
    return analytics.budget_status(user_id, args.get("year"), args.get("month"))


def _get_upcoming_obligations(user_id: str, args: dict) -> dict:
    return analytics.upcoming_obligations(user_id, days=int(args.get("days") or 30))


def _evaluate_affordability(user_id: str, args: dict) -> dict:
    if args.get("amount") is None:
        raise ToolValidationError("evaluate_affordability requires 'amount'")
    amount = affordability.validate_purchase_amount(args["amount"])
    return affordability.evaluate_affordability(user_id, amount)


def _guardian_detect(user_id: str, args: dict) -> dict:
    return guardian.detect(user_id)


TOOLS: dict[str, dict] = {
    "get_transactions": {
        "description": "Retrieve transactions (optionally date-bounded).",
        "fn": _get_transactions,
        "validate": lambda a: _require(a),
    },
    "get_monthly_summary": {
        "description": "Monthly income/expense/net/savings-rate and category distribution.",
        "fn": _get_monthly_summary,
        "validate": lambda a: _require(a),
    },
    "get_category_breakdown": {
        "description": "Spend per category with transaction counts for a period.",
        "fn": _get_category_breakdown,
        "validate": lambda a: _require(a),
    },
    "get_recurring_payments": {
        "description": "Active recurring payments with monthly/annualized costs.",
        "fn": _get_recurring_payments,
        "validate": lambda a: _require(a),
    },
    "get_financial_goals": {
        "description": "Financial goals with progress and required monthly saving.",
        "fn": _get_financial_goals,
        "validate": lambda a: _require(a),
    },
    "get_budget_status": {
        "description": "Income minus committed minus spending.",
        "fn": _get_budget_status,
        "validate": lambda a: _require(a),
    },
    "compare_periods": {
        "description": "Month-over-month change in spending and categories.",
        "fn": _compare_periods,
        "validate": lambda a: _require(a),
    },
    "detect_anomalies": {
        "description": "Explainable anomalies (spikes, duplicates, large txns, recurring-like).",
        "fn": _detect_anomalies,
        "validate": lambda a: _require(a),
    },
    "simulate_goal": {
        "description": "Goal progress and required monthly saving.",
        "fn": _simulate_goal,
        "validate": lambda a: _require(a),
    },
    "simulate_expense_change": {
        "description": "Effect of a monthly expense change on savings and goals.",
        "fn": _simulate_expense_change,
        "validate": lambda a: _require(a, "amount"),
    },
    "calculate_committed_budget": {
        "description": "Committed / spent / available / discretionary budget.",
        "fn": _calculate_committed_budget,
        "validate": lambda a: _require(a),
    },
    "get_upcoming_obligations": {
        "description": "Recurring payments due within N days.",
        "fn": _get_upcoming_obligations,
        "validate": lambda a: _require(a),
    },
    "evaluate_affordability": {
        "description": ("Decision for a one-time purchase: verdict "
                        "(AFFORDABLE/TIGHT/NOT_YET), free cash flow, cash "
                        "after purchase, comparison scenarios and goal "
                        "impacts. Requires a positive 'amount' in INR."),
        "fn": _evaluate_affordability,
        "validate": lambda a: _require(a, "amount"),
    },
    "guardian_detect": {
        "description": ("Subscription Guardian: recurring payments with price "
                        "changes (PRICE_INCREASE), high annual costs and "
                        "review signals. Produces the data behind suggested "
                        "review actions. Read-only, never executes anything."),
        "fn": _guardian_detect,
        "validate": lambda a: _require(a),
    },
}


def validate_tool(name: str, args: dict) -> None:
    if name not in TOOLS:
        raise ToolValidationError(f"Unknown tool: {name}")
    TOOLS[name]["validate"](args or {})


def execute_tool(name: str, user_id: str, args: dict) -> dict:
    validate_tool(name, args)
    return TOOLS[name]["fn"](user_id, args or {})