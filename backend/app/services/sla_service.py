"""SLA metrics for screening lag (Phase 10B)."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import Fleet, ScreeningRun, ScreeningSchedule


@dataclass(frozen=True)
class FleetSlaSummary:
    fleet_id: uuid.UUID
    fleet_name: str
    has_active_schedule: bool
    last_completed_run_id: uuid.UUID | None
    last_completed_run_at: datetime | None
    screening_lag_seconds: float | None
    screening_lag_hours: float | None
    screening_sla_ok: bool
    screening_sla_target_hours: float


def screening_max_lag_hours() -> float:
    raw = os.getenv("SLA_SCREENING_MAX_LAG_HOURS", "24").strip()
    try:
        return max(float(raw), 0.1)
    except ValueError:
        return 24.0


def screening_max_lag_seconds() -> float:
    return screening_max_lag_hours() * 3600.0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def fleet_has_active_schedule(db: Session, fleet_id: uuid.UUID) -> bool:
    count = int(
        db.execute(
            select(func.count())
            .select_from(ScreeningSchedule)
            .where(
                ScreeningSchedule.fleet_id == fleet_id,
                ScreeningSchedule.active.is_(True),
            )
        ).scalar_one()
    )
    return count > 0


def get_last_completed_parent_run(db: Session, fleet_id: uuid.UUID) -> ScreeningRun | None:
    return db.execute(
        select(ScreeningRun)
        .where(
            ScreeningRun.fleet_id == fleet_id,
            ScreeningRun.parent_run_id.is_(None),
            ScreeningRun.status == "completed",
            ScreeningRun.finished_at.isnot(None),
        )
        .order_by(ScreeningRun.finished_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def compute_fleet_sla(db: Session, fleet_id: uuid.UUID) -> FleetSlaSummary:
    fleet = db.get(Fleet, fleet_id)
    if fleet is None or not fleet.active:
        raise ValueError("艦隊が見つかりません。")

    target_hours = screening_max_lag_hours()
    has_schedule = fleet_has_active_schedule(db, fleet_id)
    last_run = get_last_completed_parent_run(db, fleet_id) if has_schedule else None

    lag_seconds: float | None = None
    lag_hours: float | None = None
    sla_ok = True

    if has_schedule:
        if last_run is None or last_run.finished_at is None:
            sla_ok = False
        else:
            finished = last_run.finished_at
            if finished.tzinfo is None:
                finished = finished.replace(tzinfo=timezone.utc)
            lag_seconds = max((_utcnow() - finished).total_seconds(), 0.0)
            lag_hours = lag_seconds / 3600.0
            sla_ok = lag_seconds <= screening_max_lag_seconds()

    return FleetSlaSummary(
        fleet_id=fleet.id,
        fleet_name=fleet.name,
        has_active_schedule=has_schedule,
        last_completed_run_id=last_run.id if last_run else None,
        last_completed_run_at=last_run.finished_at if last_run else None,
        screening_lag_seconds=lag_seconds,
        screening_lag_hours=lag_hours,
        screening_sla_ok=sla_ok,
        screening_sla_target_hours=target_hours,
    )


def list_active_schedule_fleet_ids(db: Session) -> list[uuid.UUID]:
    rows = db.execute(
        select(ScreeningSchedule.fleet_id)
        .where(ScreeningSchedule.active.is_(True))
        .distinct()
    ).all()
    return [row[0] for row in rows]


def list_fleet_sla_summaries(
    db: Session, *, fleet_id: uuid.UUID | None = None
) -> list[FleetSlaSummary]:
    if fleet_id is not None:
        return [compute_fleet_sla(db, fleet_id)]

    summaries: list[FleetSlaSummary] = []
    for fid in list_active_schedule_fleet_ids(db):
        summaries.append(compute_fleet_sla(db, fid))
    summaries.sort(key=lambda s: s.fleet_name)
    return summaries


def collect_screening_lag_metrics(db: Session) -> tuple[dict[str, float], int]:
    """Return fleet_id -> lag_seconds for Prometheus, and overdue fleet count."""
    overdue = 0
    lags: dict[str, float] = {}
    max_seconds = screening_max_lag_seconds()

    for summary in list_fleet_sla_summaries(db):
        if not summary.has_active_schedule:
            continue
        if summary.screening_lag_seconds is None:
            lags[str(summary.fleet_id)] = max_seconds + 1.0
            overdue += 1
        else:
            lags[str(summary.fleet_id)] = summary.screening_lag_seconds
            if summary.screening_lag_seconds > max_seconds:
                overdue += 1

    return lags, overdue
