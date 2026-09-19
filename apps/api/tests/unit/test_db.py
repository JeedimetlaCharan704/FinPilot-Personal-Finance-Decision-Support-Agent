from unittest.mock import patch

import pytest

from app import db


def test_client_none_when_not_configured(isolate_env):
    assert db.get_client() is None


def test_client_created_when_configured(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "secret")
    db.reset_client()
    fake = object()
    with patch("app.db.create_client", return_value=fake):
        assert db.get_client() is fake
    db.reset_client()


def test_health_not_configured(isolate_env):
    db.reset_client()
    info = db.check_db_health()
    assert info["status"] == "not_configured"
    assert "not configured" in info["message"].lower().replace("\n", " ")
    db.reset_client()


def test_health_connected(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "secret")

    class FakeTable:
        def select(self, cols):
            return self
        def limit(self, n):
            return self
        def execute(self):
            return type("R", (), {"data": []})()

    class FakeClient:
        def __init__(self):
            self._t = FakeTable()
        def table(self, name):
            return self._t

    db.reset_client()
    with patch("app.db.create_client", return_value=FakeClient()):
        info = db.check_db_health()
        assert info["status"] == "connected"
    db.reset_client()


def test_health_unreachable(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "secret")

    class Boom:
        def select(self, cols):
            raise RuntimeError("boom")
    db.reset_client()
    with patch("app.db.create_client", return_value=type("C", (), {"table": lambda self, n: Boom()})()):
        info = db.check_db_health()
        assert info["status"] == "unreachable"
    db.reset_client()


def test_fetch_rows_error_when_not_configured(isolate_env):
    with pytest.raises(db.DemoDataError):
        db.list_transactions()