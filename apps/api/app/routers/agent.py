"""Agent router - Phase 4.

POST /api/agent/analyze  -> full agent run (intent routing + tools + logging)
GET  /api/agent/runs     -> recent agent runs for a user
GET  /api/agent/runs/{id}-> a run plus its tool calls (activity trail)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app import db
from app.schemas import AgentAnalyzeRequest, AgentAnalyzeResponse
from app.services import intents, orchestrator

router = APIRouter(tags=["agent"])


@router.post("/agent/analyze", response_model=AgentAnalyzeResponse)
def analyze(payload: AgentAnalyzeRequest) -> AgentAnalyzeResponse:
    if not payload.user_id or db.get_user_by_id(payload.user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        return orchestrator.run_agent(payload.user_id, payload.question)
    except orchestrator.AgentAuthError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/agent/runs")
def list_runs(user_id: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)):
    if db.get_user_by_id(user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    runs = db.list_agent_runs(user_id, limit=limit)
    out = []
    for r in runs:
        r.pop("user_id", None)
        out.append(r)
    return {"runs": out, "count": len(out)}


@router.get("/agent/runs/{run_id}")
def run_detail(run_id: str):
    run = db.get_agent_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Agent run not found")
    run.pop("user_id", None)
    tool_calls = db.list_agent_tool_calls(run_id)
    for t in tool_calls:
        t.pop("agent_run_id", None)
    return {"run": run, "tool_calls": tool_calls,
            "intent_label": intents.intent_label(run.get("intent", "") or "")}