# LLM provider layer (Phase 5).
#
# The LLM is an UNTRUSTED PLANNER. It classifies intents, proposes tool plans
# and drafts the final explanation. It NEVER:
#   - calculates financial amounts (deterministic engine only)
#   - executes tools or SQL (the tool registry is the only executor)
#   - approves / executes financial actions (drafts are human-approved)
#
# The application must remain fully functional without any LLM: every LLM
# stage falls back to the deterministic Phase 4 engine.
from __future__ import annotations

from app.llm.base import LLMError, LLMProvider
from app.llm.factory import get_provider

__all__ = ["LLMError", "LLMProvider", "get_provider"]