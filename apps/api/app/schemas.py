# Pydantic request/response models for the Phase 4 agentic engine.
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AgentAnalyzeRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="Demo user uuid")
    question: str = Field(..., min_length=3, max_length=500)


class EvidenceItem(BaseModel):
    label: str
    value: str
    detail: str = ""


class CalculationItem(BaseModel):
    formula: str
    value: str
    detail: str = ""


class ActivityStep(BaseModel):
    step: str
    tool: str = ""
    latency_ms: int = 0
    status: str = "completed"
    detail: str = ""


class RecommendedAction(BaseModel):
    id: str = ""
    action_type: str
    title: str
    description: str = ""


class DecisionGoalImpact(BaseModel):
    """Impact of the purchase on one financial goal (deterministic)."""
    goal: str
    goal_id: str = ""
    target_amount: float = 0.0
    remaining: float = 0.0
    progress_pct: float = 0.0
    months_baseline: int | None = None
    months_after_purchase: int | None = None
    delay_months: int | None = None
    impact: str = "unchanged"  # "delayed" | "accelerated" | "unchanged"
    required_monthly_baseline: float | None = None
    required_monthly_scenario: float | None = None


class DecisionScenario(BaseModel):
    """One deterministic affordability alternative (STEP 5)."""
    label: str
    amount: float = 0.0
    cash_after_purchase: float | None = None
    months_to_save: int | None = None
    goal_delay_months: int | None = None
    detail: str = ""


class AffordDecision(BaseModel):
    """Structured "Can I afford this?" decision (STEP 3 contract).

    Every number originates from the deterministic engine — the LLM never
    computes any of these values.
    """
    verdict: str  # "AFFORDABLE" | "TIGHT" | "NOT_YET" | "INSUFFICIENT_DATA"
    purchase_amount: float
    projected_income: float
    committed_outflows: float
    normal_discretionary_spend: float
    free_cash: float
    cash_after_purchase: float
    months_to_save: int | None = None
    goal_impacts: list[DecisionGoalImpact] = []
    scenarios: list[DecisionScenario] = []
    assumptions: list[str] = []


class AgentAnalyzeResponse(BaseModel):
    run_id: str
    intent: str
    answer: str
    insights: list[str] = []
    evidence: list[EvidenceItem] = []
    calculations: list[CalculationItem] = []
    assumptions: list[str] = []
    recommended_actions: list[RecommendedAction] = []
    activity: list[ActivityStep] = []
    latency_ms: int = 0
    # Phase 5: how the answer was produced and which model assisted.
    mode: str = "deterministic"  # "llm" | "deterministic"
    model: str = ""
    warnings: list[str] = []
    # Phase 6: structured affordability decision (present for
    # afford_purchase intents with a parseable amount).
    decision: AffordDecision | None = None


class SimulationRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    scenario_type: Literal["purchase", "monthly_spend", "rent_increase",
                           "extra_savings", "cancel_subscription"]
    name: str = Field("", max_length=120)
    amount: float = Field(..., gt=0)
    frequency: Literal["one_time", "monthly"] = "one_time"
    duration_months: int = Field(1, ge=1, le=120)
    reference_id: str = Field("", max_length=64)


class ScenarioSnapshot(BaseModel):
    label: str
    monthly_income: float
    monthly_expenses: float
    monthly_savings: float
    savings_rate: float
    committed: float


class SimulationResponse(BaseModel):
    simulation_id: str
    scenario_type: str
    baseline: ScenarioSnapshot
    scenario: ScenarioSnapshot
    difference: dict
    goal_impact: dict
    explanation: str = ""
    assumptions: list[str] = []