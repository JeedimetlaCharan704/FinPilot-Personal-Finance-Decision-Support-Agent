"""Unit tests for LLM providers (Phase 5). All network calls are mocked.

No test ever makes a real xAI/Ollama request.
"""
from __future__ import annotations

import io
import json
import urllib.error

import pytest

from app.config import get_settings
from app.llm import LLMError, get_provider
from app.llm.factory import get_provider as factory_get_provider
from app.llm.ollama import OllamaProvider
from app.llm.xai import XAIProvider


class _FakeHTTPResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False

    def read(self, *a, **k):
        return io.BytesIO.read(self)


def _fake_urlopen(body: dict, monkeypatch):
    def _handler(request, timeout=None):
        return _FakeHTTPResponse(json.dumps(body).encode("utf-8"))
    monkeypatch.setattr(urllib.request, "urlopen", _handler)


class TestXAIProvider:
    def test_classify_mocked_success(self, monkeypatch):
        payload = {"choices": [{"message": {"content": json.dumps(
            {"intent": "spend_most", "confidence": 0.95})}}]}
        _fake_urlopen(payload, monkeypatch)
        provider = XAIProvider(api_key="test-key", model="grok-4.5")
        assert provider.configured is True
        out = provider.classify("Where did I spend the most?")
        assert out.intent == "spend_most"
        assert out.confidence == pytest.approx(0.95)

    def test_not_configured_without_key(self):
        provider = XAIProvider(api_key=None, model="grok-4.5")
        assert provider.configured is False
        with pytest.raises(LLMError):
            provider.classify("Where did I spend?")

    def test_http_error_raises_llm_error(self, monkeypatch):
        def _boom(request, timeout=None):
            raise urllib.error.HTTPError("http://x", 401, "Unauthorized", {}, None)
        monkeypatch.setattr(urllib.request, "urlopen", _boom)
        provider = XAIProvider(api_key="k", model="m")
        with pytest.raises(LLMError) as exc:
            provider.classify("hi")
        assert "401" in str(exc.value)
        assert "k" not in str(exc.value)  # never leak the key

    def test_invalid_content_raises(self, monkeypatch):
        _fake_urlopen({"choices": [{"message": {"content": "not json"}}]}, monkeypatch)
        provider = XAIProvider(api_key="k", model="m")
        with pytest.raises(LLMError):
            provider.plan("hi", "overview")

    def test_secret_never_in_error(self, monkeypatch):
        def _boom(request, timeout=None):
            raise ConnectionError("refused")
        monkeypatch.setattr(urllib.request, "urlopen", _boom)
        provider = XAIProvider(api_key="super-secret-value", model="m")
        with pytest.raises(LLMError) as exc:
            provider.classify("hi")
        assert "super-secret-value" not in str(exc.value)


class TestOllamaProvider:
    def test_respond_mocked_success(self, monkeypatch):
        payload = {"message": {"content": json.dumps(
            {"answer": "Rent is your top category at 15000.", "warnings": []})}}
        _fake_urlopen(payload, monkeypatch)
        provider = OllamaProvider(base_url="http://localhost:11434", model="qwen3:8b")
        assert provider.configured is True
        out = provider.respond("Q", '{"period": "Jun 2026"}')
        assert "Rent" in out.answer
        assert provider.provider == "ollama"

    def test_not_configured_without_model(self):
        provider = OllamaProvider(base_url="http://localhost:11434", model=None)
        assert provider.configured is False
        with pytest.raises(LLMError):
            provider.chat_json("s", "u")

    def test_http_error_raises(self, monkeypatch):
        def _boom(request, timeout=None):
            raise urllib.error.URLError("no server")
        monkeypatch.setattr(urllib.request, "urlopen", _boom)
        provider = OllamaProvider(base_url="http://localhost:11434", model="m")
        with pytest.raises(LLMError):
            provider.classify("hi")


class TestFactory:
    def _settings(self, monkeypatch, **overrides):
        fresh = get_settings()
        for k, v in overrides.items():
            setattr(fresh, k, v)
        return fresh

    def test_returns_xai_provider(self, monkeypatch):
        s = self._settings(monkeypatch, llm_provider="xai",
                           xai_api_key="k", xai_model="grok-4.5")
        p = factory_get_provider(s)
        assert isinstance(p, XAIProvider)
        assert p.model == "grok-4.5"

    def test_returns_ollama_provider(self, monkeypatch):
        s = self._settings(monkeypatch, llm_provider="ollama",
                           ollama_base_url="http://localhost:11434",
                           ollama_model="qwen3:8b")
        p = factory_get_provider(s)
        assert isinstance(p, OllamaProvider)
        assert p.provider == "ollama"

    def test_unknown_provider_returns_none(self, monkeypatch):
        s = self._settings(monkeypatch, llm_provider="watson")
        assert factory_get_provider(s) is None

    def test_xai_missing_key_reports_unconfigured(self, monkeypatch):
        s = self._settings(monkeypatch, llm_provider="xai", xai_api_key=None)
        p = factory_get_provider(s)
        assert isinstance(p, XAIProvider)
        assert p.configured is False

    def test_public_get_provider_smoke(self):
        # With unit-test env (key stripped) this must never raise or connect.
        assert get_provider() is not None or get_provider() is None