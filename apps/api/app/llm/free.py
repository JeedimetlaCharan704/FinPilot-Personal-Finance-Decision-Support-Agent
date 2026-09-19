# Free, keyless OpenAI-compatible provider (Phase 5 live smoke path).
#
# Pollinations.ai exposes an OpenAI-compatible chat completions endpoint that
# needs NO API key (https://text.pollinations.ai/openai). This provider sends
# no Authorization header and retries a few times because the free backend
# occasionally returns reasoning-only responses with an empty "content" field.
from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.llm.base import LLMError, LLMProvider

_DEFAULT_ENDPOINT = "https://text.pollinations.ai/openai"
_DEFAULT_MODEL = "openai"  # free routing -> gpt-4o-mini / gpt-oss family
_MAX_TOKENS = 700
_TIMEOUT_SECONDS = 90
_RETRIES = 2


class FreeProvider(LLMProvider):
    provider = "free"

    def __init__(self, model: str = _DEFAULT_MODEL,
                 endpoint: str = _DEFAULT_ENDPOINT, timeout: int = _TIMEOUT_SECONDS,
                 retries: int = _RETRIES):
        self.model = model
        self._endpoint = endpoint
        self._timeout = timeout
        self._retries = retries

    @property
    def configured(self) -> bool:
        return bool(self.model)

    def chat_json(self, system: str, user: str) -> dict:
        if not self.configured:
            raise LLMError("Free provider is not configured")
        payload = {
            "model": self.model,
            "max_tokens": _MAX_TOKENS,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self._endpoint, data=data,
                                         headers={"Content-Type": "application/json"},
                                         method="POST")
        last_error = "unknown"
        for _attempt in range(self._retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self._timeout) as response:
                    body = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                last_error = f"Free API HTTP {exc.code}"
                continue
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = f"Free API unreachable: {exc.__class__.__name__}"
                continue
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = "Free API returned invalid JSON"
                continue

            try:
                content = body["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                content = None
            if not content:
                last_error = "Free API returned empty content (reasoning-only response)"
                continue
            try:
                parsed = json.loads(content)
            except (json.JSONDecodeError, ValueError):
                last_error = "Free API returned non-JSON content"
                continue
            if not isinstance(parsed, dict):
                last_error = "Free API returned non-object JSON"
                continue
            return parsed
        raise LLMError(f"Free provider failed after retries: {last_error}")