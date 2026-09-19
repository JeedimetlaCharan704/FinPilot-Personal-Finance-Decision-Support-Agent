# xAI / Grok provider (Phase 5).
#
# OpenAI-compatible chat completions against https://api.x.ai/v1. Uses only
# stdlib urllib so no new dependency is required. The API key is read from
# server settings only and is never logged or exposed to the browser.
from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.llm.base import LLMError, LLMProvider

_DEFAULT_ENDPOINT = "https://api.x.ai/v1/chat/completions"
_TIMEOUT_SECONDS = 45


class XAIProvider(LLMProvider):
    provider = "xai"

    def __init__(self, api_key: str | None, model: str | None,
                 endpoint: str = _DEFAULT_ENDPOINT, timeout: int = _TIMEOUT_SECONDS):
        self._api_key = api_key
        self.model = model or ""
        self._endpoint = endpoint
        self._timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self._api_key and self.model)

    def chat_json(self, system: str, user: str) -> dict:
        if not self.configured:
            raise LLMError("xAI provider is not configured (missing XAI_API_KEY)")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self._endpoint, data=data, headers=headers,
                                         method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            raise LLMError(f"xAI API HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise LLMError(f"xAI API unreachable: {exc.__class__.__name__}") from exc
        except (json.JSONDecodeError, ValueError) as exc:
            raise LLMError("xAI API returned invalid JSON") from exc

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("xAI API response missing message content") from exc
        try:
            return json.loads(content)
        except (json.JSONDecodeError, ValueError) as exc:
            raise LLMError("xAI API returned non-JSON content") from exc