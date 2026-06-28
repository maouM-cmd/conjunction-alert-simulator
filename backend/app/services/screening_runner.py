"""Execute a screening run using batch analysis."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from backend.app.db.models import ScreeningRun
from backend.app.services import fleet_service, screening_service
from backend.app.services.batch_analysis import MAX_SATELLITES, run_batch_conjunction_analysis
from backend.app.services.webhook_notifier import notify_batch_fleet_events


class ScreeningRunnerError(Exception):
    pass


def execute_screening_run(db: Session, run_id: uuid.UUID) -> ScreeningRun:
    run = screening_service.get_run(db, run_id)
    if run.status not in ("pending", "failed"):
        return run

    screening_service.mark_run_running(db, run)

    schedule = None
    if run.schedule_id is not None:
        schedule = screening_service.get_schedule(db, run.schedule_id)

    try:
        satellites, total = fleet_service.list_satellites(
            db, run.fleet_id, limit=MAX_SATELLITES, offset=0
        )
        if not satellites:
            return screening_service.mark_run_completed(
                db,
                run,
                satellite_count=0,
                event_count=0,
                degraded=False,
                computation_time_ms=0,
            )

        degraded = total > MAX_SATELLITES
        tle_list = [s.tle for s in satellites]

        threshold_km = schedule.threshold_km if schedule else 5.0
        duration_days = schedule.duration_days if schedule else 7.0
        step_minutes = schedule.step_minutes if schedule else 1
        use_advanced_pc = schedule.use_advanced_pc if schedule else False
        use_altitude_prefilter = schedule.use_altitude_prefilter if schedule else True
        auto_spacetrack_cdm = schedule.auto_spacetrack_cdm if schedule else False
        spacetrack_cdm_pc_min = schedule.spacetrack_cdm_pc_min if schedule else None

        batch = run_batch_conjunction_analysis(
            tle_list,
            duration_days=duration_days,
            threshold_km=threshold_km,
            step_minutes=step_minutes,
            parallel=len(tle_list) > 1,
            use_advanced_pc=use_advanced_pc,
            use_anisotropic_cov=use_advanced_pc,
            use_altitude_prefilter=use_altitude_prefilter,
            auto_spacetrack_cdm=auto_spacetrack_cdm,
            spacetrack_cdm_pc_min=spacetrack_cdm_pc_min,
        )

        if schedule and schedule.notify_on_complete:
            notify_batch_fleet_events(batch.results)

        return screening_service.mark_run_completed(
            db,
            run,
            satellite_count=len(tle_list),
            event_count=batch.summary.total_events,
            degraded=degraded,
            computation_time_ms=batch.computation_time_ms,
        )
    except Exception as exc:
        screening_service.mark_run_failed(db, run, error_message=str(exc))
        raise ScreeningRunnerError(str(exc)) from exc
