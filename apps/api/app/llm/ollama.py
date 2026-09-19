# Ollama provider (Phase 5, optional fallback).
#
# Talks to a local Ollama server (default http://localhost:11434) using its
# /api/chat endpoint with "format": "json" for structured output. Stdlib only.
from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.llm.base import LLMError, LLMProvider

_TIMEOUT_SECONDS = 120


class OllamaProvider(LLMProvider):
    provider = "ollama"

    def __init__(self, base_url: str | None, model: str | None,
                 timeout: int = _TIMEOUT_SECONDS):
        self._base_url = (base_url or "http://localhost:11434").rstrip("/")
        self.model = model or ""
        self._timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.model)

    def chat_json(self, system: str, user: str) -> dict:
        if not self.configured:
            raise LLMError("Ollama provider is not configured (missing OLLAMA_MODEL)")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
        url = f"{self._base_url}/api/chat"
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data,
                                         headers={"Content-Type": "application/json"},
                                         method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise LLMError(f"Ollama API HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise LLMError(f"Ollama unreachable: {exc.__class__.__name__}") from exc
        except (json.JSONDecodeError, ValueError) as exc:
            raise LLMError("Ollama API returned invalid JSON") from exc

        try:
            content = body["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMError("Ollama API response missing message content") from exc
        try:
            return json.loads(content)
        except (json.JSONDecodeError, ValueError) as exc:
            raise LLMError("Ollama API returned non-JSON content") from exc