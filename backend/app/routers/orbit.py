"""Orbit propagation API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import OrbitPointOut, OrbitRequest, OrbitResponse, PositionKm
from backend.app.services.analysis import run_orbit_analysis

router = APIRouter(prefix="/api/v1", tags=["orbit"])


@router.post("/orbit", response_model=OrbitResponse)
def orbit_api(body: OrbitRequest) -> OrbitResponse:
    try:
        parsed, points = run_orbit_analysis(
            body.tle,
            body.duration_days,
            body.step_minutes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return OrbitResponse(
        name=parsed.name,
        norad_id=parsed.norad_id,
        points=[
            OrbitPointOut(
                time=p.time,
                position_km=PositionKm(
                    x=round(p.position_km[0], 4),
                    y=round(p.position_km[1], 4),
                    z=round(p.position_km[2], 4),
                ),
            )
            for p in points
        ],
    )
