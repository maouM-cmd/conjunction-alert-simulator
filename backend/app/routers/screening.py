"""Scheduled screening REST API (Phase 9B)."""

from __future__ import annotations

import uuid
from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.auth.api_key import (
    AuthPrincipal,
    check_fleet_access,
    get_auth_principal,
    principal_scoped_fleet_id,
)
from backend.app.db.models import ScreeningRun, ScreeningSchedule
from backend.app.db.session import get_session_factory, require_screening
from backend.app.models.schemas import (
    ScreeningRunListOut,
    ScreeningRunOut,
    ScreeningRunStatus,
    ScreeningScheduleCreate,
    ScreeningScheduleOut,
    ScreeningScheduleUpdate,
)
from backend.app.services import screening_service
from backend.app.services.auth_config import is_api_key_required
from backend.app.tasks.screening_tasks import run_screening_job

router = APIRouter(prefix="/api/v1/screening", tags=["screening"])


def _screening_db() -> Generator[Session, None, None]:
    require_screening()
    factory = get_session_factory()
    assert factory is not None
    db = factory()
    try:
        yield db
    finally:
        db.close()


def _parse_uuid(value: str, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"無効な {label} です。") from exc


def _handle_service_error(exc: screening_service.ScreeningServiceError) -> HTTPException:
    if isinstance(exc, screening_service.NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, screening_service.ValidationError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


def _schedule_out(schedule: ScreeningSchedule) -> ScreeningScheduleOut:
    return ScreeningScheduleOut(
        id=str(schedule.id),
        fleet_id=str(schedule.fleet_id),
        name=schedule.name,
        cron_expression=schedule.cron_expression,
        threshold_km=schedule.threshold_km,
        duration_days=schedule.duration_days,
        step_minutes=schedule.step_minutes,
        use_advanced_pc=schedule.use_advanced_pc,
        use_altitude_prefilter=schedule.use_altitude_prefilter,
        auto_spacetrack_cdm=schedule.auto_spacetrack_cdm,
        spacetrack_cdm_pc_min=schedule.spacetrack_cdm_pc_min,
        notify_on_complete=schedule.notify_on_complete,
        active=schedule.active,
        last_run_at=schedule.last_run_at,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
    )


def _run_out(run: ScreeningRun) -> ScreeningRunOut:
    return ScreeningRunOut(
        id=str(run.id),
        schedule_id=str(run.schedule_id) if run.schedule_id else None,
        fleet_id=str(run.fleet_id),
        status=run.status,  # type: ignore[arg-type]
        started_at=run.started_at,
        finished_at=run.finished_at,
        satellite_count=run.satellite_count,
        event_count=run.event_count,
        degraded=run.degraded,
        retry_count=run.retry_count,
        error_message=run.error_message,
        computation_time_ms=run.computation_time_ms,
        created_at=run.created_at,
    )


def _resolve_fleet_filter(
    principal: AuthPrincipal, fleet_id: str | None
) -> uuid.UUID | None:
    if is_api_key_required() and not principal.is_admin:
        scoped = principal_scoped_fleet_id(principal)
        if scoped is not None:
            return scoped
    return _parse_uuid(fleet_id, "fleet_id") if fleet_id else None


@router.post("/schedules", response_model=ScreeningScheduleOut, status_code=201)
def create_schedule(
    body: ScreeningScheduleCreate,
    db: Session = Depends(_screening_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> ScreeningScheduleOut:
    fleet_id = _parse_uuid(body.fleet_id, "fleet_id")
    check_fleet_access(principal, fleet_id)
    try:
        schedule = screening_service.create_schedule(
            db,
            fleet_id=fleet_id,
            name=body.name,
            cron_expression=body.cron_expression,
            threshold_km=body.threshold_km,
            duration_days=body.duration_days,
            step_minutes=body.step_minutes,
            use_advanced_pc=body.use_advanced_pc,
            use_altitude_prefilter=body.use_altitude_prefilter,
            auto_spacetrack_cdm=body.auto_spacetrack_cdm,
            spacetrack_cdm_pc_min=body.spacetrack_cdm_pc_min,
            notify_on_complete=body.notify_on_complete,
            api_key_id=principal.api_key.id if principal.api_key else None,
        )
    except screening_service.ScreeningServiceError as exc:
        raise _handle_service_error(exc) from exc
    return _schedule_out(schedule)


@router.get("/schedules", response_model=list[ScreeningScheduleOut])
def list_schedules(
    db: Session = Depends(_screening_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
    fleet_id: str | None = None,
) -> list[ScreeningScheduleOut]:
    fid = _resolve_fleet_filter(principal, fleet_id)
    if is_api_key_required() and principal_scoped_fleet_id(principal) is not None and fleet_id:
        requested = _parse_uuid(fleet_id, "fleet_id")
        check_fleet_access(principal, requested)
    schedules = screening_service.list_schedules(db, fleet_id=fid)
    return [_schedule_out(s) for s in schedules]


@router.get("/schedules/{schedule_id}", response_model=ScreeningScheduleOut)
def get_schedule(
    schedule_id: str,
    db: Session = Depends(_screening_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> ScreeningScheduleOut:
    sid = _parse_uuid(schedule_id, "schedule_id")
    try:
        schedule = screening_service.get_schedule(db, sid)
    except screening_service.ScreeningServiceError as exc:
        raise _handle_service_error(exc) from exc
    check_fleet_access(principal, schedule.fleet_id)
    return _schedule_out(schedule)


@router.patch("/schedules/{schedule_id}", response_model=ScreeningScheduleOut)
def update_schedule(
    schedule_id: str,
    body: ScreeningScheduleUpdate,
    db: Session = Depends(_screening_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> ScreeningScheduleOut:
    sid = _parse_uuid(schedule_id, "schedule_id")
    try:
        existing = screening_service.get_schedule(db, sid)
        check_fleet_access(principal, existing.fleet_id)
        schedule = screening_service.update_schedule(
            db,
            sid,
            api_key_id=principal.api_key.id if principal.api_key else None,
            **body.model_dump(exclude_unset=True),
        )
    except screening_service.ScreeningServiceError as exc:
        raise _handle_service_error(exc) from exc
    return _schedule_out(schedule)


@router.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: str,
    db: Session = Depends(_screening_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> None:
    sid = _parse_uuid(schedule_id, "schedule_id")
    try:
        existing = screening_service.get_schedule(db, sid)
        check_fleet_access(principal, existing.fleet_id)
        screening_service.delete_schedule(
            db, sid, api_key_id=principal.api_key.id if principal.api_key else None
        )
    except screening_service.ScreeningServiceError as exc:
        raise _handle_service_error(exc) from exc


@router.post("/schedules/{schedule_id}/run", response_model=ScreeningRunOut, status_code=202)
def trigger_schedule_run(
    schedule_id: str,
    db: Session = Depends(_screening_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> ScreeningRunOut:
    sid = _parse_uuid(schedule_id, "schedule_id")
    try:
        schedule = screening_service.get_schedule(db, sid)
        check_fleet_access(principal, schedule.fleet_id)
        run = screening_service.create_run(db, fleet_id=schedule.fleet_id, schedule_id=schedule.id)
    except screening_service.ScreeningServiceError as exc:
        raise _handle_service_error(exc) from exc
    run_screening_job.delay(str(run.id))
    run = screening_service.get_run(db, run.id)
    return _run_out(run)


@router.get("/runs", response_model=ScreeningRunListOut)
def list_runs(
    db: Session = Depends(_screening_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
    fleet_id: str | None = None,
    status: ScreeningRunStatus | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> ScreeningRunListOut:
    fid = _resolve_fleet_filter(principal, fleet_id)
    if is_api_key_required() and principal_scoped_fleet_id(principal) is not None and fleet_id:
        requested = _parse_uuid(fleet_id, "fleet_id")
        check_fleet_access(principal, requested)
    items, total = screening_service.list_runs(
        db, fleet_id=fid, status=status, limit=limit, offset=offset
    )
    return ScreeningRunListOut(
        items=[_run_out(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/runs/{run_id}", response_model=ScreeningRunOut)
def get_run(
    run_id: str,
    db: Session = Depends(_screening_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> ScreeningRunOut:
    rid = _parse_uuid(run_id, "run_id")
    try:
        run = screening_service.get_run(db, rid)
    except screening_service.ScreeningServiceError as exc:
        raise _handle_service_error(exc) from exc
    check_fleet_access(principal, run.fleet_id)
    return _run_out(run)
