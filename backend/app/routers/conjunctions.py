"""Conjunction detection API."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import (
    AnalysisWindow,
    ConjunctionOut,
    ConjunctionsRequest,
    ConjunctionsResponse,
    SatelliteInfo,
)
from backend.app.services.analysis import run_conjunction_analysis

router = APIRouter(prefix="/api/v1", tags=["conjunctions"])

COMPUTATION_TIMEOUT_SEC = 90.0


@router.post("/conjunctions", response_model=ConjunctionsResponse)
async def detect_conjunctions_api(body: ConjunctionsRequest) -> ConjunctionsResponse:
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                run_conjunction_analysis,
                body.tle,
                body.duration_days,
                body.threshold_km,
                body.step_minutes,
            ),
            timeout=COMPUTATION_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="接近解析がタイムアウトしました（90秒超）。期間や刻みを短くしてください。",
        ) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    conjunctions = [
        ConjunctionOut(
            debris_norad_id=e.debris_norad_id,
            debris_name=e.debris_name,
            debris_tle=e.debris_tle,
            tca=e.tca,
            miss_distance_km=round(e.miss_distance_km, 4),
            relative_velocity_kms=round(e.relative_velocity_kms, 4),
            risk_level=e.risk_level,  # type: ignore[arg-type]
        )
        for e in result.events
        if e.risk_level in ("high", "medium", "low")
    ]

    return ConjunctionsResponse(
        satellite=SatelliteInfo(
            name=result.satellite.name,
            norad_id=result.satellite.norad_id,
        ),
        analysis_window=AnalysisWindow(start=result.start, end=result.end),
        threshold_km=result.threshold_km,
        conjunctions=conjunctions,
        debris_catalog_count=result.debris_catalog_count,
        computation_time_ms=result.computation_time_ms,
        tle_cache_stale=result.tle_cache_stale,
    )
