"""Integration tests — only run when a real Supabase project is configured.
Automatically skipped otherwise (see conftest.py).

These exercise the REAL database over the network. They never contain or
require real user credentials and never leak secrets.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_api_db_health_connected_and_repo_reads():
    """Full stack check: FastAPI -> repository -> live Supabase."""
    r = client.get("/api/db/health")
    assert r.status_code == 200, r.text
    assert r.json()["database"] == "connected"

    from app import db as repo

    user = repo.get_demo_user()
    assert user is not None, "Expected the seeded demo user to exist"

    tx = repo.list_transactions()
    assert tx, "Expected seeded demo transactions to exist"