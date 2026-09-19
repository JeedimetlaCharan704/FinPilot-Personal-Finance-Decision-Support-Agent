"""Shared pytest fixtures. Unit tests NEVER touch a live Supabase."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch):
    """Delete optional secrets from the env so unit tests are hermetic."""
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: requires a live Supabase project")


def pytest_collection_modifyitems(config, items):
    if config.getoption("-m") == "not integration":
        return
    if is_supabase_configured():
        return
    # If Supabase isn't configured, integration tests are marked to auto-skip.
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(
                pytest.mark.skipif(True, reason="SUPABASE_URL not set; integration test skipped")
            )


def is_supabase_configured() -> bool:
    import os
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))