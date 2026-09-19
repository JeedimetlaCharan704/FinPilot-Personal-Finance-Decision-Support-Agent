"""Unit tests for the free keyless LLM provider. All network calls are mocked.

No test ever makes a real Pollinations request.
"""
from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

import pytest

from app.config import get_settings
from app.llm import LLMError
from app.llm.factory import get_provider as factory_get_provider
from app.llm.free import FreeProvider


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


class TestFreeProvider:
    def test_classify_mocked_success(self, monkeypatch):
        _fake_urlopen({"choices": [{"message": {"content": json.dumps(
            {"intent": "spend_most", "confidence": 0.95})}}]}, monkeypatch)
        provider = FreeProvider()
        assert provider.configured is True
        out = provider.classify("Where did I spend the most?")
        assert out.intent == "spend_most"
        assert out.confidence == pytest.approx(0.95)
        assert provider.provider == "free"

    def test_retries_on_empty_content(self, monkeypatch):
        calls = {"n": 0}

        def _handler(request, timeout=None):
            calls["n"] += 1
            if calls["n"] == 1:
                body = {"choices": [{"message": {"role": "assistant",
                                                 "reasoning": "..."}}]}
            else:
                body = {"choices": [{"message": {"content": json.dumps(
                    {"intent": "overview", "confidence": 0.9})}}]}
            return _FakeHTTPResponse(json.dumps(body).encode("utf-8"))
        monkeypatch.setattr(urllib.request, "urlopen", _handler)
        provider = FreeProvider()
        out = provider.classify("hi")
        assert out.intent == "overview"
        assert calls["n"] == 2

    def test_persistent_empty_content_raises(self, monkeypatch):
        def _handler(request, timeout=None):
            return _FakeHTTPResponse(json.dumps(
                {"choices": [{"message": {"role": "assistant",
                                          "reasoning": "..."}}]}).encode("utf-8"))
        monkeypatch.setattr(urllib.request, "urlopen", _handler)
        provider = FreeProvider(retries=2)
        with pytest.raises(LLMError):
            provider.classify("hi")

    def test_http_error_raises_after_retries(self, monkeypatch):
        def _boom(request, timeout=None):
            raise urllib.error.HTTPError("http://x", 429, "Too Many", {}, None)
        monkeypatch.setattr(urllib.request, "urlopen", _boom)
        provider = FreeProvider(retries=1)
        with pytest.raises(LLMError) as exc:
            provider.classify("hi")
        assert "429" in str(exc.value)

    def test_non_json_content_raises(self, monkeypatch):
        _fake_urlopen({"choices": [{"message": {"content": "oops"}}]}, monkeypatch)
        provider = FreeProvider()
        with pytest.raises(LLMError):
            provider.plan("hi", "overview")

    def test_invalid_content_object_raises(self, monkeypatch):
        _fake_urlopen({"choices": [{"message": {"content": "[1, 2, 3]"}}]},
                      monkeypatch)
        provider = FreeProvider()
        with pytest.raises(LLMError):
            provider.respond("q", "{}")

    def test_no_auth_header_sent(self, monkeypatch):
        captured = {}

        def _handler(request, timeout=None):
            captured["auth"] = request.get_header("Authorization")
            return _FakeHTTPResponse(json.dumps(
                {"choices": [{"message": {"content": json.dumps(
                    {"intent": "overview", "confidence": 0.9})}}]}).encode("utf-8"))
        monkeypatch.setattr(urllib.request, "urlopen", _handler)
        FreeProvider().classify("hi")
        assert captured["auth"] is None


class TestFactoryFree:
    def test_returns_free_provider(self):
        s = get_settings()
        setattr(s, "llm_provider", "free")
        provider = factory_get_provider(s)
        assert isinstance(provider, FreeProvider)
        assert provider.model == "openai"
        assert provider.configured is True