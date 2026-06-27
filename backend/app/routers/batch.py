"""Batch conjunction analysis API."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import (
    AnalysisWindow,
    BatchConjunctionsRequest,
    BatchConjunctionsResponse,
    BatchSummaryOut,
    ConjunctionOut,
    ConjunctionsResponse,
    SatelliteInfo,
)
from backend.app.services.batch_analysis import run_batch_conjunction_analysis

router = APIRouter(prefix="/api/v1", tags=["batch"])

BATCH_TIMEOUT_SEC = 600.0


def _to_conjunctions_response(result) -> ConjunctionsResponse:
    conjunctions = [
        ConjunctionOut(
            debris_norad_id=e.debris_norad_id,
            debris_name=e.debris_name,
            debris_tle=e.debris_tle,
            tca=e.tca,
            miss_distance_km=round(e.miss_distance_km, 4),
            relative_velocity_kms=round(e.relative_velocity_kms, 4),
            risk_level=e.risk_level,  # type: ignore[arg-type]
            pc=e.pc,
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
        tle_provider=result.tle_provider,
    )


@router.post("/conjunctions/batch", response_model=BatchConjunctionsResponse)
async def batch_conjunctions_api(body: BatchConjunctionsRequest) -> BatchConjunctionsResponse:
    tle_list = [s.tle for s in body.satellites]
    try:
        batch = await asyncio.wait_for(
            asyncio.to_thread(
                run_batch_conjunction_analysis,
                tle_list,
                body.duration_days,
                body.threshold_km,
                body.step_minutes,
                body.sigma_km,
            ),
            timeout=BATCH_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="一括接近解析がタイムアウトしました（600秒超）。",
        ) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    results = [_to_conjunctions_response(r) for r in batch.results]
    summary = batch.summary
    return BatchConjunctionsResponse(
        results=results,
        summary=BatchSummaryOut(
            satellite_count=summary.satellite_count,
            total_events=summary.total_events,
            highest_pc=summary.highest_pc,
            highest_pc_satellite=summary.highest_pc_satellite,
            highest_pc_debris=summary.highest_pc_debris,
        ),
        computation_time_ms=batch.computation_time_ms,
        tle_provider=batch.tle_provider,
    )
