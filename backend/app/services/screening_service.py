"""Screening schedule and run management."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from croniter import croniter
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import ScreeningRun, ScreeningSchedule
from backend.app.services import fleet_service

MAX_SCREENING_SATELLITES = 25
DUE_WINDOW_SECONDS = 90


class ScreeningServiceError(Exception):
    pass


class NotFoundError(ScreeningServiceError):
    pass


class ValidationError(ScreeningServiceError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def validate_cron_expression(expression: str) -> str:
    expr = expression.strip()
    parts = expr.split()
    if len(parts) != 5:
        raise ValidationError("cron 式は5フィールド（分 時 日 月 曜）で指定してください。")
    try:
        croniter(expr)
    except (ValueError, KeyError) as exc:
        raise ValidationError(f"無効な cron 式です: {exc}") from exc
    return expr


def is_schedule_due(schedule: ScreeningSchedule, now: datetime | None = None) -> bool:
    if not schedule.active:
        return False
    now = now or _utcnow()
    try:
        itr = croniter(schedule.cron_expression, now)
        prev_fire = itr.get_prev(datetime)
    except (ValueError, KeyError):
        return False
    if prev_fire.tzinfo is None:
        prev_fire = prev_fire.replace(tzinfo=timezone.utc)
    if (now - prev_fire).total_seconds() > DUE_WINDOW_SECONDS:
        return False
    if schedule.last_run_at is not None and schedule.last_run_at >= prev_fire:
        return False
    return True


def create_schedule(
    db: Session,
    *,
    fleet_id: uuid.UUID,
    name: str,
    cron_expression: str,
    threshold_km: float = 5.0,
    duration_days: float = 7.0,
    step_minutes: int = 1,
    use_advanced_pc: bool = False,
    use_altitude_prefilter: bool = True,
    auto_spacetrack_cdm: bool = False,
    spacetrack_cdm_pc_min: float | None = None,
    notify_on_complete: bool = False,
) -> ScreeningSchedule:
    fleet_service.get_fleet(db, fleet_id)
    if auto_spacetrack_cdm and not use_advanced_pc:
        raise ValidationError("auto_spacetrack_cdm=true の場合は use_advanced_pc=true が必要です。")
    schedule = ScreeningSchedule(
        fleet_id=fleet_id,
        name=name,
        cron_expression=validate_cron_expression(cron_expression),
        threshold_km=threshold_km,
        duration_days=duration_days,
        step_minutes=step_minutes,
        use_advanced_pc=use_advanced_pc,
        use_altitude_prefilter=use_altitude_prefilter,
        auto_spacetrack_cdm=auto_spacetrack_cdm,
        spacetrack_cdm_pc_min=spacetrack_cdm_pc_min,
        notify_on_complete=notify_on_complete,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def list_schedules(db: Session, *, fleet_id: uuid.UUID | None = None) -> list[ScreeningSchedule]:
    stmt = select(ScreeningSchedule).where(ScreeningSchedule.active.is_(True))
    if fleet_id is not None:
        stmt = stmt.where(ScreeningSchedule.fleet_id == fleet_id)
    return list(db.execute(stmt.order_by(ScreeningSchedule.created_at.desc())).scalars().all())


def get_schedule(db: Session, schedule_id: uuid.UUID) -> ScreeningSchedule:
    schedule = db.get(ScreeningSchedule, schedule_id)
    if schedule is None or not schedule.active:
        raise NotFoundError("スクリーニングスケジュールが見つかりません。")
    return schedule


def update_schedule(
    db: Session,
    schedule_id: uuid.UUID,
    **fields,
) -> ScreeningSchedule:
    schedule = get_schedule(db, schedule_id)
    if "cron_expression" in fields and fields["cron_expression"] is not None:
        fields["cron_expression"] = validate_cron_expression(fields["cron_expression"])
    if fields.get("auto_spacetrack_cdm") and not fields.get(
        "use_advanced_pc", schedule.use_advanced_pc
    ):
        raise ValidationError("auto_spacetrack_cdm=true の場合は use_advanced_pc=true が必要です。")
    for key, value in fields.items():
        if value is not None and hasattr(schedule, key):
            setattr(schedule, key, value)
    schedule.updated_at = _utcnow()
    db.commit()
    db.refresh(schedule)
    return schedule


def delete_schedule(db: Session, schedule_id: uuid.UUID) -> None:
    schedule = get_schedule(db, schedule_id)
    schedule.active = False
    schedule.updated_at = _utcnow()
    db.commit()


def list_due_schedules(db: Session, now: datetime | None = None) -> list[ScreeningSchedule]:
    now = now or _utcnow()
    active = list_schedules(db)
    return [s for s in active if is_schedule_due(s, now)]


def create_run(
    db: Session,
    *,
    fleet_id: uuid.UUID,
    schedule_id: uuid.UUID | None = None,
) -> ScreeningRun:
    if schedule_id is not None:
        schedule = get_schedule(db, schedule_id)
        if schedule.fleet_id != fleet_id:
            raise ValidationError("fleet_id がスケジュールと一致しません。")
    else:
        fleet_service.get_fleet(db, fleet_id)
    run = ScreeningRun(
        schedule_id=schedule_id,
        fleet_id=fleet_id,
        status="pending",
    )
    db.add(run)
    if schedule_id is not None:
        schedule = get_schedule(db, schedule_id)
        schedule.last_run_at = _utcnow()
        schedule.updated_at = _utcnow()
    db.commit()
    db.refresh(run)
    return run


def create_chunk_run(
    db: Session,
    *,
    fleet_id: uuid.UUID,
    schedule_id: uuid.UUID | None,
    parent_run_id: uuid.UUID,
    chunk_index: int,
) -> ScreeningRun:
    run = ScreeningRun(
        schedule_id=schedule_id,
        fleet_id=fleet_id,
        parent_run_id=parent_run_id,
        chunk_index=chunk_index,
        status="pending",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def list_child_runs(db: Session, parent_run_id: uuid.UUID) -> list[ScreeningRun]:
    return list(
        db.execute(
            select(ScreeningRun)
            .where(ScreeningRun.parent_run_id == parent_run_id)
            .order_by(ScreeningRun.chunk_index)
        )
        .scalars()
        .all()
    )


def increment_parent_chunk_completion(db: Session, parent: ScreeningRun) -> ScreeningRun:
    parent.completed_chunks += 1
    db.commit()
    db.refresh(parent)
    return parent


def get_run(db: Session, run_id: uuid.UUID) -> ScreeningRun:
    run = db.get(ScreeningRun, run_id)
    if run is None:
        raise NotFoundError("スクリーニング Run が見つかりません。")
    return run


def list_runs(
    db: Session,
    *,
    fleet_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[ScreeningRun], int]:
    filters = []
    if fleet_id is not None:
        filters.append(ScreeningRun.fleet_id == fleet_id)
    if status is not None:
        filters.append(ScreeningRun.status == status)
    count_stmt = select(func.count()).select_from(ScreeningRun)
    list_stmt = select(ScreeningRun)
    if filters:
        count_stmt = count_stmt.where(*filters)
        list_stmt = list_stmt.where(*filters)
    total = int(db.execute(count_stmt).scalar_one())
    items = list(
        db.execute(list_stmt.order_by(ScreeningRun.created_at.desc()).limit(limit).offset(offset))
        .scalars()
        .all()
    )
    return items, total


def mark_run_running(db: Session, run: ScreeningRun) -> ScreeningRun:
    run.status = "running"
    run.started_at = _utcnow()
    db.commit()
    db.refresh(run)
    return run


def mark_run_completed(
    db: Session,
    run: ScreeningRun,
    *,
    satellite_count: int,
    event_count: int,
    degraded: bool,
    computation_time_ms: int,
) -> ScreeningRun:
    run.status = "completed"
    run.finished_at = _utcnow()
    run.satellite_count = satellite_count
    run.event_count = event_count
    run.degraded = degraded
    run.computation_time_ms = computation_time_ms
    run.error_message = None
    db.commit()
    db.refresh(run)
    return run


def mark_run_failed(
    db: Session,
    run: ScreeningRun,
    *,
    error_message: str,
    dead_letter: bool = False,
    retry_count: int | None = None,
) -> ScreeningRun:
    run.status = "dead_letter" if dead_letter else "failed"
    run.finished_at = _utcnow()
    run.error_message = error_message[:2000]
    if retry_count is not None:
        run.retry_count = retry_count
    db.commit()
    db.refresh(run)
    return run
