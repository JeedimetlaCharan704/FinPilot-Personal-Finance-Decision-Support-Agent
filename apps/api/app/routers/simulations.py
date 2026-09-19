"""Decision simulation router - Phase 4 flagship."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app import db
from app.schemas import SimulationRequest, SimulationResponse
from app.services import simulations

router = APIRouter(tags=["simulations"])


@router.post("/simulations", response_model=SimulationResponse)
def run_simulation(payload: SimulationRequest) -> SimulationResponse:
    if db.get_user_by_id(payload.user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    result = simulations.run_simulation(
        payload.user_id, payload.scenario_type, payload.name, payload.amount,
        payload.frequency, payload.duration_months, payload.reference_id)
    if result.get("error") == "no_data":
        raise HTTPException(status_code=422, detail="No transaction data available for simulation")

    sim_id = db.create_simulation(
        payload.user_id,
        name=result["scenario"].get("label", payload.name or "Scenario"),
        amount=payload.amount,
        verdict="",  # decision-support only: no verdict is issued
        projected_free_cash=result["scenario"]["monthly_savings"],
        goal_impact=result["goal_impact"],
        scenarios={"baseline": result["baseline"], "scenario": result["scenario"],
                   "difference": result["difference"]},
    )
    return SimulationResponse(
        simulation_id=sim_id,
        scenario_type=payload.scenario_type,
        baseline=result["baseline"], scenario=result["scenario"],
        difference=result["difference"], goal_impact=result["goal_impact"],
        explanation=result["explanation"], assumptions=result["assumptions"],
    )


@router.get("/simulations")
def list_simulations(user_id: str = Query(..., min_length=1),
                     limit: int = Query(20, ge=1, le=100)):
    if db.get_user_by_id(user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    rows = db.list_simulations(user_id, limit=limit)
    for r in rows:
        r.pop("user_id", None)
    return {"simulations": rows, "count": len(rows)}