# Provider selection (Phase 5).
#
# LLM_PROVIDER=xai   -> XAIProvider (Grok via https://api.x.ai)
# LLM_PROVIDER=ollama-> OllamaProvider (local, optional)
# LLM_PROVIDER=free  -> FreeProvider (keyless Pollinations.ai endpoint)
# anything else      -> None (pure deterministic mode; the app stays useful).
from __future__ import annotations

from app.config import get_settings
from app.llm.base import LLMProvider
from app.llm.free import FreeProvider
from app.llm.ollama import OllamaProvider
from app.llm.xai import XAIProvider


def get_provider(settings=None) -> LLMProvider | None:
    """Build the configured LLM provider, or None when unavailable/unknown.

    A provider may still report configured=False (e.g. xAI without a key);
    callers check provider.configured before use.
    """
    s = settings if settings is not None else get_settings()
    name = (s.llm_provider or "").strip().lower()
    if name == "xai":
        return XAIProvider(api_key=s.xai_api_key, model=s.xai_model)
    if name == "ollama":
        return OllamaProvider(base_url=s.ollama_base_url, model=s.ollama_model)
    if name == "free":
        return FreeProvider()
    return None