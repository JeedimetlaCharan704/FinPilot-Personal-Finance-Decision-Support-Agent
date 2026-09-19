"""Shared pytest fixtures. Unit tests NEVER touch a live Supabase.

Isolation strategy:
- Unit tests run with the Supabase/XAI env vars SET TO EMPTY STRING, which
  overrides any real values that may exist in the repo-root .env file
  (pydantic-settings reads process env with higher priority than the dotenv
  file). This keeps unit tests fully hermetic even when .env is configured.
- Integration tests must NOT be isolated: they read real values from .env via
  app.config.get_settings() and exercise the live Supabase project.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch, request):
    """Force empty secrets for unit tests; leave integration tests untouched."""
    marker = request.node.get_closest_marker("integration")
    if marker is None:
        # Empty string overrides .env file values (see module docstring).
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
        monkeypatch.setenv("SUPABASE_URL", "")
        monkeypatch.setenv("XAI_API_KEY", "")
        # Drop the cached Settings so pydantic re-reads the env.
        from app.config import get_settings
        get_settings.cache_clear()
        # Forget any Supabase client a previous (integration) test may have built.
        from app import db
        db.reset_client()
    yield


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
    from app.config import get_settings
    settings = get_settings()
    return settings.supabase_configured