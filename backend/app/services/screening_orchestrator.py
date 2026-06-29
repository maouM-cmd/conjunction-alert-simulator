"""Chunked screening orchestration (Phase 9D)."""

from __future__ import annotations

import math
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import ConjunctionAlert, ScreeningRun
from backend.app.services import alert_service, fleet_service, screening_service
from backend.app.services import pc_refinement_service
from backend.app.services.batch_analysis import run_batch_conjunction_analysis
from backend.app.services.scale_config import fleet_max_satellites, screening_chunk_size
from backend.app.services.webhook_notifier import notify_new_alerts


class ScreeningOrchestratorError(Exception):
    pass


def _schedule_params(schedule) -> dict:
    if schedule is None:
        return {
            "threshold_km": 5.0,
            "duration_days": 7.0,
            "step_minutes": 1,
            "use_advanced_pc": False,
            "use_altitude_prefilter": True,
            "auto_spacetrack_cdm": False,
            "spacetrack_cdm_pc_min": None,
            "notify_on_complete": False,
        }
    return {
        "threshold_km": schedule.threshold_km,
        "duration_days": schedule.duration_days,
        "step_minutes": schedule.step_minutes,
        "use_advanced_pc": schedule.use_advanced_pc,
        "use_altitude_prefilter": schedule.use_altitude_prefilter,
        "auto_spacetrack_cdm": schedule.auto_spacetrack_cdm,
        "spacetrack_cdm_pc_min": schedule.spacetrack_cdm_pc_min,
        "notify_on_complete": schedule.notify_on_complete,
    }


def _run_batch_for_satellites(satellites, params: dict):
    tle_list = [s.tle for s in satellites]
    chunk_limit = screening_chunk_size()
    return run_batch_conjunction_analysis(
        tle_list,
        duration_days=params["duration_days"],
        threshold_km=params["threshold_km"],
        step_minutes=params["step_minutes"],
        parallel=len(tle_list) > 1,
        max_workers=None,
        use_advanced_pc=params["use_advanced_pc"],
        use_anisotropic_cov=params["use_advanced_pc"],
        use_altitude_prefilter=params["use_altitude_prefilter"],
        auto_spacetrack_cdm=params["auto_spacetrack_cdm"],
        spacetrack_cdm_pc_min=params["spacetrack_cdm_pc_min"],
        max_satellites=chunk_limit,
        prefer_screening_workers=True,
    )


def execute_screening_run(db: Session, run_id: uuid.UUID) -> ScreeningRun:
    run = screening_service.get_run(db, run_id)
    if run.status not in ("pending", "failed"):
        return run

    if run.parent_run_id is not None:
        return _execute_chunk_run(db, run)

    screening_service.mark_run_running(db, run)
    schedule = (
        screening_service.get_schedule(db, run.schedule_id) if run.schedule_id else None
    )
    params = _schedule_params(schedule)

    satellites = fleet_service.list_all_active_satellites(
        db, run.fleet_id, max_count=fleet_max_satellites()
    )
    if not satellites:
        return screening_service.mark_run_completed(
            db, run, satellite_count=0, event_count=0, degraded=False, computation_time_ms=0
        )

    chunk_size = screening_chunk_size()
    if len(satellites) <= chunk_size:
        return _execute_single_chunk_on_run(db, run, satellites, params, schedule)

    num_chunks = math.ceil(len(satellites) / chunk_size)
    run.chunk_total = num_chunks
    run.completed_chunks = 0
    run.satellite_count = len(satellites)
    db.commit()

    from backend.app.tasks.screening_tasks import run_screening_chunk

    for index in range(num_chunks):
        child = screening_service.create_chunk_run(
            db,
            fleet_id=run.fleet_id,
            schedule_id=run.schedule_id,
            parent_run_id=run.id,
            chunk_index=index,
        )
        run_screening_chunk.delay(str(child.id))

    db.refresh(run)
    return run


def _execute_single_chunk_on_run(
    db: Session,
    run: ScreeningRun,
    satellites,
    params: dict,
    schedule,
) -> ScreeningRun:
    try:
        batch = _run_batch_for_satellites(satellites, params)
        satellite_by_norad = {s.norad_id: s.id for s in satellites}
        new_opens = alert_service.ingest_screening_results(
            db,
            run_id=run.id,
            fleet_id=run.fleet_id,
            results=batch.results,
            satellite_by_norad=satellite_by_norad,
        )
        pc_refinement_service.enqueue_auto_refine_for_alerts(new_opens)
        if schedule and params["notify_on_complete"]:
            _notify_parent_cycle_alerts(db, run, [run.id])
        return screening_service.mark_run_completed(
            db,
            run,
            satellite_count=len(satellites),
            event_count=batch.summary.total_events,
            degraded=False,
            computation_time_ms=batch.computation_time_ms,
        )
    except Exception as exc:
        screening_service.mark_run_failed(db, run, error_message=str(exc))
        raise ScreeningOrchestratorError(str(exc)) from exc


def _execute_chunk_run(db: Session, run: ScreeningRun) -> ScreeningRun:
    if run.status not in ("pending", "failed"):
        return run

    screening_service.mark_run_running(db, run)
    parent = screening_service.get_run(db, run.parent_run_id)
    schedule = (
        screening_service.get_schedule(db, run.schedule_id) if run.schedule_id else None
    )
    params = _schedule_params(schedule)
    chunk_size = screening_chunk_size()
    offset = (run.chunk_index or 0) * chunk_size

    try:
        satellites, _total = fleet_service.list_satellites(
            db, run.fleet_id, limit=chunk_size, offset=offset
        )
        if not satellites:
            screening_service.mark_run_completed(
                db, run, satellite_count=0, event_count=0, degraded=False, computation_time_ms=0
            )
            return _maybe_finalize_parent(db, parent, schedule, params)

        batch = _run_batch_for_satellites(satellites, params)
        satellite_by_norad = {s.norad_id: s.id for s in satellites}
        new_opens = alert_service.ingest_screening_results(
            db,
            run_id=run.id,
            fleet_id=run.fleet_id,
            results=batch.results,
            satellite_by_norad=satellite_by_norad,
        )
        pc_refinement_service.enqueue_auto_refine_for_alerts(new_opens)
        screening_service.mark_run_completed(
            db,
            run,
            satellite_count=len(satellites),
            event_count=batch.summary.total_events,
            degraded=False,
            computation_time_ms=batch.computation_time_ms,
        )
        return _maybe_finalize_parent(db, parent, schedule, params)
    except Exception as exc:
        screening_service.mark_run_failed(db, run, error_message=str(exc))
        screening_service.mark_run_failed(db, parent, error_message=f"chunk failed: {exc}")
        raise ScreeningOrchestratorError(str(exc)) from exc


def _maybe_finalize_parent(db: Session, parent: ScreeningRun, schedule, params: dict) -> ScreeningRun:
    parent = screening_service.increment_parent_chunk_completion(db, parent)
    if parent.chunk_total is None or parent.completed_chunks < parent.chunk_total:
        db.refresh(parent)
        return parent

    children = screening_service.list_child_runs(db, parent.id)
    total_events = sum(c.event_count for c in children)
    total_ms = sum(c.computation_time_ms or 0 for c in children)
    failed = [c for c in children if c.status in ("failed", "dead_letter")]
    if failed:
        screening_service.mark_run_failed(
            db,
            parent,
            error_message=f"{len(failed)} chunk(s) failed",
        )
        return parent

    if schedule and params["notify_on_complete"]:
        child_ids = [c.id for c in children]
        _notify_parent_cycle_alerts(db, parent, child_ids)

    return screening_service.mark_run_completed(
        db,
        parent,
        satellite_count=parent.satellite_count or sum(c.satellite_count for c in children),
        event_count=total_events,
        degraded=False,
        computation_time_ms=total_ms,
    )


def _notify_parent_cycle_alerts(db: Session, parent: ScreeningRun, run_ids: list[uuid.UUID]) -> None:
    if parent.started_at is None:
        return
    alerts = list(
        db.execute(
            select(ConjunctionAlert).where(
                ConjunctionAlert.screening_run_id.in_(run_ids),
                ConjunctionAlert.created_at >= parent.started_at,
            )
        )
        .scalars()
        .all()
    )
    for alert in alerts:
        db.refresh(alert, attribute_names=["satellite"])
    if alerts:
        notify_new_alerts(alerts)
