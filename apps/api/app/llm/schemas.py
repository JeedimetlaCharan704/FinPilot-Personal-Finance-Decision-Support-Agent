# Pydantic schemas for LLM structured output (Phase 5).
#
# These describe what we ACCEPT from an LLM. Anything else is rejected and the
# orchestrator falls back to the deterministic engine.
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LLMIntentOut(BaseModel):
    """Structured intent classification result from the LLM."""

    intent: str
    reason: str = ""
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class LLMToolCall(BaseModel):
    """One proposed tool invocation. Names must exist in the registry."""

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class LLMToolPlan(BaseModel):
    """Structured tool plan from the LLM. Validated against the registry."""

    intent: str
    reason: str = ""
    tools: list[LLMToolCall] = Field(default_factory=list)


class LLMAnswerOut(BaseModel):
    """Final response draft from the LLM.

    'evidence_refs' are optional human-readable references the model reports
    (e.g. "tool=get_monthly_summary metric=income period=Jun 2026"); they are
    advisory only. The authoritative evidence always comes from the
    deterministic engine.
    """

    answer: str = Field(..., min_length=1)
    warnings: list[str] = Field(default_factory=list)
    uncertainty: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)