# LLM provider abstraction (Phase 5).
#
# Providers only know how to *talk to a model* with a system/user prompt and
# return structured JSON. Prompting is shared here so every provider behaves
# identically; the tool registry (services.tools) remains the source of truth
# for what may actually execute.
from __future__ import annotations

from abc import ABC, abstractmethod

from app.llm.schemas import LLMAnswerOut, LLMIntentOut, LLMToolPlan
from app.llm.validation import (
    MAX_AMOUNT,
    TOOL_ALLOWED_ARGS,
    validate_answer,
    validate_intent,
    validate_tool_plan,
)
from app.services.tools import TOOLS


class LLMError(Exception):
    """Transport/parse failure talking to an LLM provider."""


_INTENT_LIST = (
    "overview, spend_most, category_amount, subscriptions, what_changed, "
    "afford_purchase, rent_increase, committed, goal_save, goal_track, "
    "upcoming, anomaly"
)


def _tool_catalog() -> str:
    lines = []
    for name, meta in TOOLS.items():
        allowed = ", ".join(sorted(TOOL_ALLOWED_ARGS.get(name, ()))) or "none"
        lines.append(f"- {name}: {meta['description']} (allowed arguments: {allowed})")
    return "\n".join(lines)


class LLMProvider(ABC):
    """Common interface: classify() / plan() / respond().

    Concrete subclasses implement chat_json() only.
    """

    provider: str = "base"
    model: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.model)

    @abstractmethod
    def chat_json(self, system: str, user: str) -> dict:
        """Send a chat completion and return the parsed JSON object."""

    # --- intent classification -------------------------------------------
    def classify(self, question: str) -> LLMIntentOut:
        system = (
            "You are FinPilot's intent classifier. You classify a user's "
            "financial question into exactly one intent. "
            f"Allowed intents: {_INTENT_LIST}. "
            "Reply with a JSON object only: "
            '{"intent": string, "reason": string, "confidence": number 0..1}. '
            "Never execute anything. Never answer the question itself."
        )
        raw = self.chat_json(system, question)
        out = validate_intent(raw)
        if out is None:
            raise LLMError("LLM returned an invalid intent classification")
        return out

    # --- tool planning ----------------------------------------------------
    def plan(self, question: str, intent: str) -> LLMToolPlan:
        catalog = _tool_catalog()
        system = (
            "You are FinPilot's tool planner. You propose a minimal plan of "
            "internal tools that answer the user's financial question.\n"
            "Available tools (name: description; allowed arguments):\n"
            f"{catalog}\n\n"
            "Rules:\n"
            "- Use ONLY tool names from the list above.\n"
            "- Use ONLY the listed argument keys; never invent keys.\n"
            "- 'amount' must be a positive number in INR, at most "
            f"{MAX_AMOUNT:,.0f}.\n"
            "- 'limit' is an integer 1..1000; 'days' an integer 1..365; "
            "'year' an integer; 'month' 1..12.\n"
            "- Reply with a JSON object only:\n"
            '{"intent": string, "reason": string, '
            '"tools": [{"name": string, "arguments": {}}]}\n'
            "- The LLM never computes numbers; tools compute numbers."
        )
        raw = self.chat_json(system, f"Intent: {intent}\nQuestion: {question}")
        out = validate_tool_plan(raw)
        if out is None:
            raise LLMError("LLM returned an invalid tool plan")
        return out

    # --- final response generation ----------------------------------------
    def respond(self, question: str, context: str, retry_note: str = "") -> LLMAnswerOut:
        system = (
            "You are FinPilot's financial explainer. You write the final "
            "natural-language answer for the user.\n\n"
            "HARD RULES:\n"
            "- Use ONLY the financial figures present in the supplied "
            "'verified context'. Never invent amounts, transactions, balances, "
            "income, expenses or goal impacts.\n"
            "- Never claim an action was executed or approved.\n"
            "- Clearly distinguish explanation from calculation; if data is "
            "insufficient, say so and express uncertainty.\n"
            "- Decision-support only: no investment advice, no financial "
            "product recommendations, no autonomous financial actions.\n"
            "- Reply with a JSON object only:\n"
            '{"answer": string, "warnings": [string], '
            '"uncertainty": string|null, "evidence_refs": [string]}\n'
            "- The answer must be concise (2-5 sentences) and grounded."
        )
        user = f"Question: {question}\n\nVerified context (JSON):\n{context}"
        if retry_note:
            user += f"\n\nCorrection from the system:\n{retry_note}"
        out = validate_answer(self.chat_json(system, user))
        if out is None:
            raise LLMError("LLM returned an invalid final answer")
        return out