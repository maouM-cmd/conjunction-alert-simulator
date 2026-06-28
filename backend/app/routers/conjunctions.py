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
from backend.app.services.conjunction_out import event_to_conjunction_out
from backend.app.services.webhook_notifier import notify_conjunction_events

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
                True,
                body.sigma_km,
                body.use_advanced_pc,
                body.use_anisotropic_cov if body.use_advanced_pc else False,
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
        event_to_conjunction_out(e)
        for e in result.events
        if e.risk_level in ("high", "medium", "low")
    ]

    if body.notify_webhook:
        await asyncio.to_thread(
            notify_conjunction_events,
            result.satellite,
            result.events,
        )

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
        tle_provider=result.tle_provider,
    )
