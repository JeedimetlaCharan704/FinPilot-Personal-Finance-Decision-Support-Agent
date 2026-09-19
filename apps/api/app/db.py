# DB layer — lazy Supabase client + repository functions (Phase 3 foundation).
#
# Server-side ONLY. Uses the service-role key. Never expose to the browser.
# Scope: config validation, client init, basic reads for the demo foundation.
# No financial calculations, no agent logic, no autonomous actions.
from __future__ import annotations

from typing import Any

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


_client = None


def get_client():
    """Lazily build and cache the Supabase client (server-side service role)."""
    global _client
    if _client is None:
        _client = create_supabase_client()
    return _client


def reset_client() -> None:
    """Forget the cached client AND re-read settings (used by tests)."""
    global _client
    _client = None
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
# Repositories (Phase 3 foundation — reads only; NO calculations)
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


def list_categories() -> list[dict[str, Any]]:
    return fetch_rows("categories", columns="id,name,category_type")


def list_transactions(limit: int = 500) -> list[dict[str, Any]]:
    return fetch_rows("transactions", limit=limit)


def list_recurring_payments() -> list[dict[str, Any]]:
    return fetch_rows("recurring_payments", columns="id,merchant,amount,next_payment_date,status")


def list_goals() -> list[dict[str, Any]]:
    return fetch_rows("financial_goals", columns="id,name,target_amount,current_amount,target_date")