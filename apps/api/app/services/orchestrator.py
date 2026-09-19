# Agent orchestrator (Phase 4).
#
# Flow: authenticate -> understand intent -> plan tools -> execute tools
#        (logging every tool call) -> reason over structured results ->
#        produce an evidence-grounded answer -> record the agent run.
#
# The reasoning is deterministic and grounded: every number in the answer
# originates from a tool result computed from the database. No raw
# transaction history is sent to any LLM (no LLM is required at all).
from __future__ import annotations

import json
import time

from app import db
from app.schemas import (
    ActivityStep, AgentAnalyzeResponse, CalculationItem, EvidenceItem,
    RecommendedAction,
)
from app.services import intents, tools


class AgentAuthError(Exception):
    """User could not be authenticated."""


def _inr(v: float) -> str:
    return f"\u20b9{v:,.0f}"


def _month_name(month: int) -> str:
    return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
            "Oct", "Nov", "Dec"][month - 1]


def _clip(obj: dict, max_chars: int = 6000) -> dict:
    """Keep tool outputs small before persisting (never store raw history)."""
    text = json.dumps(obj, default=str)
    if len(text) <= max_chars:
        return obj
    return {"_truncated": True, "summary": text[: max_chars]}


def run_agent(user_id: str, question: str) -> AgentAnalyzeResponse:
    started = time.perf_counter()

    user = db.get_user_by_id(user_id)
    if user is None:
        raise AgentAuthError("User not found")

    intent_info = intents.plan_tools(question)
    intent = intent_info["intent"]
    tool_names = intent_info["tools"]

    run_id = db.create_agent_run(user_id, question, intent=intent)
    activity: list[ActivityStep] = [
        ActivityStep(step="Intent detected", tool=f"router ({intent})",
                     latency_ms=1, status="completed",
                     detail=f"confidence {intent_info['confidence']}")
    ]

    results: dict[str, dict] = {}
    for tool_name in tool_names:
        args: dict = {}
        if tool_name == "get_transactions":
            args = {"limit": 50}
        call_start = time.perf_counter()
        call_id = db.create_agent_tool_call(run_id, tool_name, args)
        try:
            out = tools.execute_tool(tool_name, user_id, args)
            db.complete_agent_tool_call(call_id, _clip(out))
            results[tool_name] = out
            latency = int((time.perf_counter() - call_start) * 1000)
            detail = _tool_detail(tool_name, out)
            activity.append(ActivityStep(step="Tool executed", tool=tool_name,
                                         latency_ms=latency, status="completed",
                                         detail=detail))
        except Exception as exc:  # pragma: no cover - defensive
            db.complete_agent_tool_call(call_id, {"error": str(exc)}, status="failed")
            results[tool_name] = {"error": str(exc)}
            activity.append(ActivityStep(step="Tool failed", tool=tool_name,
                                         latency_ms=int((time.perf_counter() - call_start) * 1000),
                                         status="failed", detail=str(exc)))

    payload = build_response(intent, question, results)
    answer = payload["answer"]

    recommendations = _recommendations(user_id, results)
    for rec in recommendations:
        action_id = db.create_action_draft(
            user_id, rec["action_type"], rec["title"], rec.get("description", ""),
            payload={"source": "agent", "run_id": run_id})
        payload["recommended_actions"].append(
            RecommendedAction(id=action_id, action_type=rec["action_type"],
                              title=rec["title"], description=rec.get("description", "")))

    latency_ms = int((time.perf_counter() - started) * 1000)
    db.complete_agent_run(
        run_id, "completed",
        final_response=json.dumps({"answer": answer, "intent": intent},
                                  default=str),
        started_at=None)

    activity.append(ActivityStep(step="Response generated", tool="responder",
                                 latency_ms=latency_ms, status="completed",
                                 detail=f"{len(payload['evidence'])} evidence items"))
    return AgentAnalyzeResponse(
        run_id=run_id, intent=intent, answer=answer,
        insights=payload["insights"], evidence=payload["evidence"],
        calculations=payload["calculations"], assumptions=payload["assumptions"],
        recommended_actions=payload["recommended_actions"],
        activity=activity, latency_ms=latency_ms)


def _tool_detail(tool_name: str, out: dict) -> str:
    try:
        if tool_name == "get_category_breakdown":
            cats = out.get("categories", [])
            return f"{len(cats)} categories, total {_inr(out.get('total_expenses', 0))}" if cats else "no categories"
        if tool_name == "get_monthly_summary":
            return (f"income {_inr(out.get('income', 0))}, "
                    f"expenses {_inr(out.get('expenses', 0))}, "
                    f"net {_inr(out.get('net', 0))}")
        if tool_name == "detect_anomalies":
            return f"{out.get('count', 0)} anomalies found"
        if tool_name == "get_recurring_payments":
            return (f"{out.get('payment_count', 0)} payments, "
                    f"{_inr(out.get('monthly_committed', 0))}/mo")
        if tool_name == "get_financial_goals":
            return f"{out.get('count', 0)} goals"
        if tool_name == "compare_periods":
            pct = out.get("expense_pct_change")
            return (f"spending {'+' if pct and pct > 0 else ''}{pct}% vs prev"
                    if pct is not None else "no prior data")
        if tool_name in ("calculate_committed_budget", "get_budget_status"):
            return (f"committed {_inr(out.get('committed', 0))}, "
                    f"discretionary {_inr(out.get('discretionary', 0))}")
        if tool_name == "get_upcoming_obligations":
            return f"{out.get('count', 0)} obligations within {out.get('days_horizon', 30)} days"
        if tool_name == "simulate_expense_change":
            return f"savings -> {_inr(out.get('projected_monthly_savings', 0))}"
        if tool_name == "get_transactions":
            return f"{out.get('count', 0)} transactions"
        if tool_name == "simulate_goal":
            return f"{out.get('count', 0)} goals"
    except Exception:
        pass
    return "ok"


def build_response(intent: str, question: str, results: dict) -> dict:
    """Deterministic, evidence-grounded responder per intent."""
    summary = results.get("get_monthly_summary") or {}
    breakdown = results.get("get_category_breakdown") or {}
    recurring = results.get("get_recurring_payments") or {}
    goals_res = results.get("get_financial_goals") or {}
    compares = results.get("compare_periods") or {}
    anomalies = results.get("detect_anomalies") or {}
    budget = (results.get("calculate_committed_budget")
              or results.get("get_budget_status") or {})
    sim_change = results.get("simulate_expense_change") or {}
    upcoming = results.get("get_upcoming_obligations") or {}
    transactions = results.get("get_transactions") or {}

    base = {
        "insights": summary.get("insights", []) if isinstance(summary, dict) else [],
        "evidence": [], "calculations": [], "assumptions": [],
        "recommended_actions": [], "answer": "",
    }

    def ev(label, value, detail=""):
        base["evidence"].append(EvidenceItem(label=label, value=str(value), detail=detail))

    def calc(formula, value, detail=""):
        base["calculations"].append(CalculationItem(formula=formula, value=str(value), detail=detail))

    label = _month_name(summary.get("month", 0)) if summary.get("month") else "period"

    if intent == "overview":
        base["answer"] = _overview_answer(summary)
        if summary.get("has_data"):
            ev("Period", summary.get("period_label", label))
            ev("Income", _inr(summary.get("income", 0)))
            ev("Expenses", _inr(summary.get("expenses", 0)))
            ev("Net cash flow", _inr(summary.get("net", 0)))
            ev("Savings rate", f"{summary.get('savings_rate', 0):.1f}%")
            ev("Transactions analyzed", summary.get("transactions_analyzed", 0))
            calc("income - expenses", _inr(summary.get("net", 0)))
            calc("net / income * 100", f"{summary.get('savings_rate', 0):.1f}%",
                 "savings rate")
            if anomalies.get("anomalies"):
                ev("Anomalies", len(anomalies["anomalies"]),
                   "; ".join(a["explanation"] for a in anomalies["anomalies"][:3]))

    elif intent == "spend_most":
        cats = breakdown.get("categories", [])
        if cats:
            top = cats[0]
            period_lbl = summary.get("period_label") or breakdown.get("start_date", "the period")
            base["answer"] = (f"Based on the transactions available, your largest "
                              f"spending category in {period_lbl}"
                              f" was {top["category"]} at {_inr(top["amount"])} across "
                              f"{top["transaction_count"]} transactions.")
            for c in cats[:5]:
                ev(c["category"], _inr(c["amount"]),
                   f"{c['transaction_count']} transactions")
            calc("sum(expense_amount) group by category", _inr(cats[0]["amount"]),
                 "top category")
        else:
            base["answer"] = "No expense data was found for the selected period."

    elif intent == "category_amount":
        cats = breakdown.get("categories", [])
        if cats:
            period_lbl2 = summary.get("period_label") or breakdown.get("start_date", "the period")
            base["answer"] = (f"Your spending in {period_lbl2}: " +
                              ", ".join(f"{c['category']} {_inr(c['amount'])}"
                                        f" ({c['transaction_count']} txns)" for c in cats[:6]) + ".")
            for c in cats:
                ev(c["category"], _inr(c["amount"]), f"{c['transaction_count']} transactions")
            calc("sum(expense_amount) group by category", _inr(sum(c["amount"] for c in cats)))
        else:
            base["answer"] = "No expense data found."

    elif intent == "subscriptions":
        pmts = recurring.get("payments", [])
        if pmts:
            base["answer"] = (f"You have {recurring.get('payment_count', len(pmts))} active "
                              f"recurring payments totaling {_inr(recurring.get('monthly_committed', 0))}"
                              f" per month ({_inr(recurring.get('annualized_recurring_cost', 0))} "
                              f"annualized): " +
                              ", ".join(f"{p['merchant']} {_inr(p['amount'])}"
                                        f"/{p['frequency'][:3]}" for p in pmts) + ".")
            for p in pmts:
                ev(p["merchant"], _inr(p["amount"]),
                   f"monthly commitment {_inr(p.get('monthly_commitment', p['amount']))}, "
                   f"next {p.get('next_payment_date', 'n/a')}")
            calc("sum(amount * frequency_multiplier)", _inr(recurring.get("monthly_committed", 0)))
        else:
            base["answer"] = "No active recurring payments were found."

    elif intent == "what_changed":
        if compares.get("expense_pct_change") is not None:
            pct = compares["expense_pct_change"]
            pct_word = "increased" if pct >= 0 else "decreased"
            base["answer"] = (f"Compared with the previous month, your total spending "
                              f"{pct_word} by {pct:.1f}% "
                              f"({_inr(compares.get('expense_diff', 0))}).")
            cats = compares.get("categories", {})
            changed = sorted(
                ((n, v) for n, v in cats.items() if v.get("percentage") and abs(v["percentage"]) >= 5),
                key=lambda kv: abs(kv[1]["percentage"]), reverse=True)[:5]
            for name, v in changed:
                ev(name, _inr(v.get("diff", 0)),
                   f"{v.get('current', 0):,.0f} now vs {v.get('previous', 0):,.0f} before")
            calc("current - previous", _inr(compares.get("expense_diff", 0)))
            if anomalies.get("anomalies"):
                base["assumptions"].append(
                    "Anomaly explanations reference the previous 3-month average.")
        else:
            base["answer"] = "Not enough data to compare months yet."

    elif intent in ("afford_purchase", "rent_increase"):
        if intent == "rent_increase":
            base["answer"] = _rent_answer(summary, budget, sim_change)
        else:
            base["answer"] = _afford_answer(summary, budget)
        if budget.get("has_data"):
            ev("Monthly income", _inr(budget.get("income", 0)))
            ev("Committed", _inr(budget.get("committed", 0)))
            ev("Spent", _inr(budget.get("spent", 0)))
            ev("Discretionary", _inr(budget.get("discretionary", 0)))
            calc("income - committed - spent",
                 _inr(budget.get("discretionary", 0)), "discretionary cash")
        base["assumptions"].append(
            "This is an informational analysis, not financial advice.")
        base["assumptions"].extend(budget.get("assumptions", []))

    elif intent == "committed":
        base["answer"] = (f"Your committed obligations total {_inr(budget.get('committed', 0))}"
                          f" per month. Of {_inr(budget.get('income', 0))} monthly income, that leaves "
                          f"{_inr(budget.get('available', 0))} before discretionary spending "
                          f"({_inr(budget.get('discretionary', 0))} after actual spending).")
        ev("Monthly income", _inr(budget.get("income", 0)))
        ev("Committed", _inr(budget.get("committed", 0)))
        ev("Discretionary remaining", _inr(budget.get("discretionary", 0)))
        calc("income - committed - spent", _inr(budget.get("discretionary", 0)))
        base["assumptions"].extend(budget.get("assumptions", []))

    elif intent == "goal_save":
        gl = goals_res.get("goals", [])
        if gl:
            base["answer"] = _goal_save_answer(gl)
            for g in gl:
                ev(g["name"], f"{_inr(g['current_amount'])} / {_inr(g['target_amount'])}",
                   f"{g['progress_pct']:.1f}% complete, remaining {_inr(g['remaining'])}")
                if g.get("required_monthly") is not None:
                    calc("remaining / months_to_target",
                         _inr(g["required_monthly"]), f"to reach {g['name']} by {g.get('target_date')}")
        else:
            base["answer"] = "No financial goals are set up yet."

    elif intent == "goal_track":
        gl = goals_res.get("goals", [])
        if gl:
            base["answer"] = _goal_track_answer(gl)
            for g in gl:
                ev(g["name"], f"{g['progress_pct']:.1f}%",
                   f"{_inr(g['current_amount'])} of {_inr(g['target_amount'])}")
        else:
            base["answer"] = "No financial goals found."

    elif intent == "upcoming":
        ups = upcoming.get("upcoming", [])
        if ups:
            base["answer"] = ("Upcoming obligations in the next "
                              f"{upcoming.get('days_horizon', 30)} days: " +
                              ", ".join(f"{u['merchant']} {_inr(u['amount'])} "
                                        f"({u['days_until']}d)" for u in ups) + ".")
            for u in ups:
                ev(u["merchant"], _inr(u["amount"]),
                   f"due {u['next_payment_date']} ({u['days_until']} days)")
        else:
            base["answer"] = f"No recurring payments are due in the next {upcoming.get('days_horizon', 30)} days."

    elif intent == "anomaly":
        an = anomalies.get("anomalies", [])
        if an:
            base["answer"] = f"I found {len(an)} explainable anomalies in {anomalies.get('period')}: "
            for a in an[:5]:
                base["answer"] += f" {a['explanation']}"
                ev(a["type"].replace("_", " ").title(),
                   f"{_inr(a.get('difference', 0))} ({a.get('percentage', 0)}%)",
                   a.get("threshold", ""))
        else:
            base["answer"] = f"No anomalies were detected in {anomalies.get('period', 'the period')} based on the configured thresholds."

    else:
        base["answer"] = _overview_answer(summary)

    if not base["answer"]:
        base["answer"] = "No data available to answer that yet."
    return base


def _overview_answer(summary: dict) -> str:
    if not summary.get("has_data"):
        return "No transaction data is available yet."
    return (f"In {summary.get('period_label', 'the latest month')} you earned "
            f"{_inr(summary.get('income', 0))} and spent {_inr(summary.get('expenses', 0))}, "
            f"leaving a net cash flow of {_inr(summary.get('net', 0))} "
            f"({summary.get('savings_rate', 0):.1f}% savings rate) with "
            f"{_inr(summary.get('committed', 0))} in recurring commitments.")


def _afford_answer(summary: dict, budget: dict) -> str:
    if not budget.get("has_data"):
        return "Not enough data to assess affordability yet."
    disc = budget.get("discretionary", 0)
    return (f"Based on the transactions available, your discretionary cash "
            f"(income minus recurring commitments minus actual spending) is "
            f"{_inr(disc)} per month. A large one-time purchase would need to be "
            f"covered by savings; the What-If simulator can show the exact impact "
            f"on your goals. Under this scenario, this is an informational "
            f"analysis, not financial advice — I won't tell you to buy or not buy.")


def _rent_answer(summary: dict, budget: dict, sim_change: dict) -> str:
    if sim_change.get("projected_monthly_savings") is not None:
        return (f"If rent rises by {_inr(abs(sim_change.get('monthly_savings', 0) -
                                              sim_change.get('projected_monthly_savings', 0)))} "
                f"per month, your monthly savings would fall from "
                f"{_inr(sim_change.get('monthly_savings', 0))} to "
                f"{_inr(sim_change.get('projected_monthly_savings', 0))}. "
                f"{_goal_impact_txt(sim_change.get('goal_impact', {}))}")
    return "Not enough data to simulate a rent increase."


def _goal_impact_txt(gi: dict) -> str:
    if not gi or not gi.get("goal"):
        return ""
    if gi.get("delay_months") is None:
        return ""
    if gi["delay_months"] > 0:
        return f"That would delay your '{gi['goal']}' goal by about {gi['delay_months']} month(s)."
    if gi["delay_months"] < 0:
        return f"That would accelerate your '{gi['goal']}' goal by about {-gi['delay_months']} month(s)."
    return "Your goal timeline would be unchanged."


def _goal_save_answer(goals: list) -> str:
    parts = []
    for g in goals:
        if g.get("required_monthly") is not None:
            parts.append(f"save {_inr(g['required_monthly'])}/month to reach "
                         f"'{g['name']}' by {g.get('target_date')}")
        else:
            parts.append(f"'{g['name']}' has no target date — "
                         f"remaining {_inr(g['remaining'])} at {g['progress_pct']:.1f}%")
    return "To meet your goals: " + "; ".join(parts) + "."


def _goal_track_answer(goals: list) -> str:
    parts = []
    for g in goals:
        parts.append(f"'{g['name']}' is {g['progress_pct']:.1f}% funded "
                     f"({_inr(g['current_amount'])} of {_inr(g['target_amount'])})")
    return "Goal progress: " + "; ".join(parts) + "."


def _recommendations(user_id: str, results: dict) -> list[dict]:
    """Create DRAFT action suggestions from findings (never executes anything)."""
    recs: list[dict] = []
    anomalies = results.get("detect_anomalies", {})
    for a in anomalies.get("anomalies", []):
        if a["type"] == "category_spike":
            recs.append({
                "action_type": "review",
                "title": f"Review unusually high {a['category']} spending",
                "description": a["explanation"],
            })
        elif a["type"] == "recurring_like":
            merchant = a["explanation"].split(" looks like")[0]
            recs.append({
                "action_type": "review",
                "title": f"Review recurring payment: {merchant}",
                "description": a["explanation"],
            })
        elif a["type"] == "duplicate":
            recs.append({
                "action_type": "review",
                "title": "Review possible duplicate transaction",
                "description": a["explanation"],
            })
    goals_res = results.get("get_financial_goals", {})
    for g in goals_res.get("goals", [])[:1]:
        if g["progress_pct"] < 50:
            recs.append({
                "action_type": "save",
                "title": f"Contribute more to {g['name']}",
                "description": (f"Goal is {g['progress_pct']:.1f}% funded; remaining "
                                f"{_inr(g['remaining'])}."),
            })
    return recs