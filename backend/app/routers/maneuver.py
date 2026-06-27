"""Maneuver preview API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import (
    ClosestApproachOut,
    ManeuverPreviewRequest,
    ManeuverPreviewResponse,
)
from backend.app.services.analysis import run_maneuver_preview

router = APIRouter(prefix="/api/v1", tags=["maneuver"])


@router.post("/maneuver/preview", response_model=ManeuverPreviewResponse)
def maneuver_preview_api(body: ManeuverPreviewRequest) -> ManeuverPreviewResponse:
    try:
        before, after = run_maneuver_preview(
            body.satellite_tle,
            body.debris_tle,
            body.direction,
            body.delta_v_ms,
            body.duration_days,
            body.step_minutes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ManeuverPreviewResponse(
        before=ClosestApproachOut(
            tca=before.tca,
            miss_distance_km=round(before.miss_distance_km, 4),
            relative_velocity_kms=round(before.relative_velocity_kms, 4),
        ),
        after=ClosestApproachOut(
            tca=after.tca,
            miss_distance_km=round(after.miss_distance_km, 4),
            relative_velocity_kms=round(after.relative_velocity_kms, 4),
        ),
        delta_v_applied_ms=body.delta_v_ms,
        direction=body.direction,
    )
