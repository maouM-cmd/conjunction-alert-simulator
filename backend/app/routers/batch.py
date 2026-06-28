"""Batch conjunction analysis API."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import (
    AnalysisWindow,
    BatchConjunctionsRequest,
    BatchConjunctionsResponse,
    BatchSummaryOut,
    ConjunctionsResponse,
    SatelliteInfo,
    WebhookNotifyOut,
)
from backend.app.services.batch_analysis import run_batch_conjunction_analysis
from backend.app.services.conjunction_out import event_to_conjunction_out
from backend.app.services.webhook_notifier import notify_batch_fleet_events

router = APIRouter(prefix="/api/v1", tags=["batch"])

BATCH_TIMEOUT_SEC = 600.0


def _to_conjunctions_response(result) -> ConjunctionsResponse:
    conjunctions = [
        event_to_conjunction_out(e)
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
                True,
                None,
                body.use_advanced_pc,
                body.use_anisotropic_cov if body.use_advanced_pc else False,
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

    webhook_result = None
    if body.notify_webhook:
        wh = await asyncio.to_thread(notify_batch_fleet_events, batch.results)
        webhook_result = WebhookNotifyOut(
            sent=wh.sent,
            alert_count=wh.alert_count,
            degraded=wh.degraded,
            message=wh.message,
        )

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
        parallel=batch.parallel,
        worker_count=batch.worker_count,
        webhook=webhook_result,
    )
