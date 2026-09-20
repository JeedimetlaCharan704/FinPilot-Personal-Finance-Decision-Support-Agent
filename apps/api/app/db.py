# DB layer - lazy Supabase client + repository functions.
#
# Server-side ONLY. Uses the service-role key. Never expose to the browser.
# Phase 3: config validation, client init, basic reads for the demo foundation.
# Phase 4: filtered queries + agent run / tool call / action draft / simulation
#          storage (schema from Phase 3 migrations; no schema changes here).
from __future__ import annotations

import json
import threading
from datetime import date, datetime, timezone, timedelta
from typing import Any
from uuid import uuid4

from supabase import create_client

from app.config import get_settings


class DemoDataError(Exception):
    """Raised when demo data is invalid or missing (non-fatal for DB layer)."""


# ---------------------------------------------------------------------------
# Client lifecycle (lazy, server-side only)
# ---------------------------------------------------------------------------
def create_supabase_client():
    """Return a Supabase client if config is present, else None.

    Never raises on missing config; callers must handle None.
    """
    settings = get_settings()
    if not settings.supabase_configured:
        return None

    return create_client(settings.supabase_url, settings.supabase_service_role_key)


_client_local = threading.local()


def get_client():
    """Return a per-thread Supabase client (avoids httpx thread-safety issues).

    Each FastAPI worker thread gets its own ``httpx.Client`` → its own
    ``httpcore.ConnectionPool`` → its own TCP connection to Supabase.
    This eliminates the shared-state concurrency bug that caused intermittent
    ``httpx.ReadError: [Errno 11] Resource temporarily unavailable`` under
    concurrent requests.
    """
    client = getattr(_client_local, "client", None)
    if client is None:
        client = create_supabase_client()
        _client_local.client = client
    return client


def reset_client() -> None:
    """Forget the cached client AND re-read settings (used by tests)."""
    _client_local.client = None
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Health / connectivity
# ---------------------------------------------------------------------------
def check_db_health() -> dict:
    """Return a non-secret DB health descriptor.

    Never includes credentials. States:
      - not_configured -> Supabase vars missing (or empty)
      - connected      -> client created and a trivial query succeeded
      - unreachable    -> configured but the probe failed
    """
    settings = get_settings()
    base = {"service": settings.service_name}

    client = get_client()
    if client is None:
        base["status"] = "not_configured"
        base["message"] = ("Supabase not configured. Set SUPABASE_URL and "
                           "SUPABASE_SERVICE_ROLE_KEY in your .env to enable."
                           " See .env.example.")
        return base

    try:
        # Deterministic, trivial connectivity probe against a demo table.
        client.table("categories").select("id").limit(1).execute()
        base["status"] = "connected"
        return base
    except Exception as exc:  # pragma: no cover - network dependent
        base["status"] = "unreachable"
        base["message"] = f"Supabase reachability check failed ({type(exc).__name__})."
        return base


# ---------------------------------------------------------------------------
# Repositories - Phase 3 foundation (reads only; NO calculations)
# ---------------------------------------------------------------------------
def _table(name: str):
    client = get_client()
    if client is None:
        raise DemoDataError(f"Supabase not configured; cannot query {name}.")
    return client.table(name)


def fetch_rows(table: str, columns: str = "*", limit: int | None = None) -> list[dict[str, Any]]:
    query = _table(table).select(columns)
    if limit is not None:
        query = query.limit(limit)
    rows = query.execute()
    return rows.data or []


def get_demo_user() -> dict[str, Any] | None:
    rows = fetch_rows("users", limit=1)
    return rows[0] if rows else None


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Authenticate a user id against the users table (demo auth)."""
    if not user_id:
        return None
    try:
        rows = _table("users").select("id,email,display_name,currency").eq("id", user_id).limit(1).execute()
        return rows.data[0] if rows.data else None
    except Exception:
        return None


def list_categories() -> list[dict[str, Any]]:
    return fetch_rows("categories", columns="id,name,category_type")


def list_transactions(limit: int = 500) -> list[dict[str, Any]]:
    return fetch_rows("transactions", limit=limit)


def list_recurring_payments() -> list[dict[str, Any]]:
    return fetch_rows("recurring_payments", columns="id,merchant,amount,next_payment_date,status")


def list_goals() -> list[dict[str, Any]]:
    return fetch_rows("financial_goals", columns="id,name,target_amount,current_amount,target_date")


# ---------------------------------------------------------------------------
# Phase 4 - filtered reads (indexed date/user/category queries)
# ---------------------------------------------------------------------------
_DEFAULT_TXN_COLUMNS = ("id,category_id,transaction_date,amount,transaction_type,"
                        "description,merchant,is_recurring")


def fetch_transactions(user_id: str,
                       start_date: str | None = None,
                       end_date: str | None = None,
                       limit: int | None = None,
                       columns: str = _DEFAULT_TXN_COLUMNS) -> list[dict[str, Any]]:
    """Transactions for one user, optionally bounded by date range (newest first)."""
    query = _table("transactions").select(columns).eq("user_id", user_id)
    if start_date:
        query = query.gte("transaction_date", start_date)
    if end_date:
        query = query.lte("transaction_date", end_date)
    query = query.order("transaction_date", desc=True)
    if limit is not None:
        query = query.limit(limit)
    rows = query.execute()
    return rows.data or []


def fetch_recurring(user_id: str, status: str | None = "active") -> list[dict[str, Any]]:
    query = _table("recurring_payments").select(
        "id,merchant,description,amount,frequency,next_payment_date,status,category_id"
    ).eq("user_id", user_id)
    if status:
        query = query.eq("status", status)
    rows = query.order("amount", desc=True).execute()
    return rows.data or []


def fetch_goals(user_id: str) -> list[dict[str, Any]]:
    rows = _table("financial_goals").select(
        "id,name,target_amount,current_amount,target_date,priority,status"
    ).eq("user_id", user_id).order("priority", desc=False).execute()
    return rows.data or []


# ---------------------------------------------------------------------------
# Phase 4 - agent_runs / agent_tool_calls
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_iso() -> str:
    return date.today().isoformat()


def create_agent_run(user_id: str, question: str, intent: str | None = None) -> str:
    run_id = str(uuid4())
    payload: dict[str, Any] = {
        "id": run_id,
        "user_id": user_id,
        "question": question,
        "status": "running",
        "started_at": _now_iso(),
    }
    _table("agent_runs").insert(payload).execute()
    return run_id


def complete_agent_run(run_id: str, status: str = "completed",
                       final_response: str | None = None,
                       started_at: str | None = None) -> None:
    payload: dict[str, Any] = {"status": status, "completed_at": _now_iso()}
    if final_response is not None:
        payload["final_response"] = final_response
    if started_at is not None:
        payload["started_at"] = started_at
    _table("agent_runs").update(payload).eq("id", run_id).execute()


def fail_agent_run(run_id: str, error: Exception) -> None:
    try:
        message = json.dumps({"error": str(error)})
    except Exception:
        message = "error"
    complete_agent_run(run_id, status="failed", final_response=message)


def list_agent_runs(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    rows = _table("agent_runs").select(
        "id,user_id,question,status,started_at,completed_at,final_response,created_at"
    ).eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
    return rows.data or []


def get_agent_run(run_id: str) -> dict[str, Any] | None:
    rows = _table("agent_runs").select("*").eq("id", run_id).limit(1).execute()
    return rows.data[0] if rows.data else None


def list_agent_tool_calls(run_id: str) -> list[dict[str, Any]]:
    rows = _table("agent_tool_calls").select(
        "id,agent_run_id,tool_name,input_json,output_json,status,started_at,completed_at"
    ).eq("agent_run_id", run_id).order("started_at", desc=False).execute()
    return rows.data or []


def create_agent_tool_call(run_id: str, tool_name: str, input_json: dict[str, Any]) -> str:
    call_id = str(uuid4())
    payload = {
        "id": call_id,
        "agent_run_id": run_id,
        "tool_name": tool_name,
        "input_json": input_json,
        "status": "started",
        "started_at": _now_iso(),
    }
    _table("agent_tool_calls").insert(payload).execute()
    return call_id


def complete_agent_tool_call(call_id: str, output_json: dict[str, Any],
                             status: str = "completed",
                             started_at: str | None = None) -> None:
    payload: dict[str, Any] = {
        "status": status,
        "completed_at": _now_iso(),
        "output_json": output_json,
    }
    if started_at is not None:
        payload["started_at"] = started_at
    _table("agent_tool_calls").update(payload).eq("id", call_id).execute()


# ---------------------------------------------------------------------------
# Phase 4 - action_drafts (DRAFT only; approval is a human action)
# ---------------------------------------------------------------------------
def create_action_draft(user_id: str, action_type: str, title: str,
                        description: str | None = None,
                        payload: dict[str, Any] | None = None) -> str:
    """Idempotent: returns the existing DRAFT with the same title if present."""
    existing = _table("action_drafts").select("id").eq("user_id", user_id) \
        .eq("title", title).eq("status", "draft").limit(1).execute()
    if existing.data:
        return existing.data[0]["id"]
    action_id = str(uuid4())
    row = {
        "id": action_id,
        "user_id": user_id,
        "action_type": action_type,
        "title": title,
        "description": description,
        "payload_json": payload or {},
        "status": "draft",
        "created_at": _now_iso(),
    }
    _table("action_drafts").insert(row).execute()
    return action_id


def list_action_drafts(user_id: str, status: str | None = None,
                       limit: int = 50) -> list[dict[str, Any]]:
    query = _table("action_drafts").select(
        "id,user_id,action_type,title,description,payload_json,status,approved_at,executed_at,created_at"
    ).eq("user_id", user_id)
    if status:
        query = query.eq("status", status)
    rows = query.order("created_at", desc=True).limit(limit).execute()
    return rows.data or []


def get_action_draft(action_id: str) -> dict[str, Any] | None:
    rows = _table("action_drafts").select("*").eq("id", action_id).limit(1).execute()
    return rows.data[0] if rows.data else None


def update_action_status(action_id: str, status: str) -> None:
    """Approve/reject marking. NEVER executes any financial action."""
    if status not in ("draft", "approved", "rejected", "executed"):
        raise DemoDataError(f"Invalid action status: {status}")
    payload: dict[str, Any] = {"status": status}
    if status == "approved":
        payload["approved_at"] = _now_iso()
    if status == "executed":
        payload["executed_at"] = _now_iso()
    _table("action_drafts").update(payload).eq("id", action_id).execute()


# ---------------------------------------------------------------------------
# Phase 4 - decision_simulations
# ---------------------------------------------------------------------------
def create_simulation(user_id: str, name: str, amount: float,
                      purchase_date: str | None = None,
                      verdict: str = "",
                      projected_free_cash: float | None = None,
                      goal_impact: dict[str, Any] | None = None,
                      scenarios: dict[str, Any] | None = None) -> str:
    sim_id = str(uuid4())
    row = {
        "id": sim_id,
        "user_id": user_id,
        "purchase_name": name,
        "purchase_amount": amount,
        "purchase_date": purchase_date or _today_iso(),
        "verdict": verdict or "",
        "projected_free_cash": projected_free_cash,
        "goal_impact_json": goal_impact or {},
        "scenarios_json": scenarios or {},
        "created_at": _now_iso(),
    }
    _table("decision_simulations").insert(row).execute()
    return sim_id


def list_simulations(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    rows = _table("decision_simulations").select(
        "id,user_id,purchase_name,purchase_amount,purchase_date,verdict,projected_free_cash,goal_impact_json,scenarios_json,created_at"
    ).eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
    return rows.data or []