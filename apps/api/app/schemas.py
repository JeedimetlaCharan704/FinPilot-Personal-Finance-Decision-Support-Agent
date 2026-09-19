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