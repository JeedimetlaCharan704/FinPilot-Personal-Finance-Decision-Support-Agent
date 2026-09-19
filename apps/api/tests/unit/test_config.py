from app.config import get_settings, Settings


def test_defaults():
    # _env_file=None keeps this a pure defaults test even when a real .env exists.
    s = Settings(_env_file=None)
    assert s.service_name == "finpilot-api"
    assert s.app_name == "FinPilot API"
    assert s.version == "0.3.0"
    assert s.cors_origin_list == ["http://localhost:3000"]


def test_cors_parsing():
    s = Settings(cors_origins="http://a.test, http://b.test ,", _env_file=None)
    assert s.cors_origin_list == ["http://a.test", "http://b.test"]


def test_supabase_configured_false_by_default(isolate_env):
    s = Settings(_env_file=None)
    assert s.supabase_configured is False


def test_supabase_configured_true(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "secret")
    s = Settings(_env_file=None)
    assert s.supabase_configured is True


def test_settings_is_singleton_cached():
    assert get_settings() is get_settings()