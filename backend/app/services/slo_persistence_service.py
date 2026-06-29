"""API SLO hourly bucket persistence (Phase 10J)."""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.db.models import ApiSloFleetHourlyBucket, ApiSloHourlyBucket
from backend.app.services.api_availability_service import (
    ApiAvailabilitySummary,
    api_rolling_window_hours,
    api_slo_target_percent,
    replace_memory_buckets,
    summary_from_totals,
)

_BUCKET_SECONDS = 3600
_hydrated = False


@dataclass(frozen=True)
class ApiSloDaySummary:
    day: date
    availability_ratio: float | None
    availability_percent: float | None
    request_count: int
    errors_5xx: int
    slo_ok: bool


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def slo_api_persist_enabled() -> bool:
    return os.getenv("SLA_API_PERSIST_ENABLED", "").strip().lower() in ("1", "true", "yes")


def slo_api_retention_days() -> int:
    return max(_env_int("SLA_API_RETENTION_DAYS", 90), 1)


def _current_bucket_epoch() -> int:
    now = int(time.time())
    return now - (now % _BUCKET_SECONDS)


def _window_since_epoch() -> int:
    window_seconds = int(api_rolling_window_hours() * 3600.0)
    return _current_bucket_epoch() - window_seconds


def upsert_hourly_bucket(
    db: Session,
    hour_epoch: int,
    *,
    inc_total: int = 0,
    inc_5xx: int = 0,
) -> None:
    now = datetime.now(timezone.utc)
    row = db.get(ApiSloHourlyBucket, hour_epoch)
    if row is None:
        db.add(
            ApiSloHourlyBucket(
                hour_epoch=hour_epoch,
                request_total=inc_total,
                errors_5xx=inc_5xx,
                updated_at=now,
            )
        )
    else:
        row.request_total += inc_total
        row.errors_5xx += inc_5xx
        row.updated_at = now
    db.commit()


def fetch_buckets(db: Session, since_epoch: int) -> dict[int, tuple[int, int]]:
    rows = db.execute(
        select(
            ApiSloHourlyBucket.hour_epoch,
            ApiSloHourlyBucket.request_total,
            ApiSloHourlyBucket.errors_5xx,
        ).where(ApiSloHourlyBucket.hour_epoch >= since_epoch)
    ).all()
    return {int(row[0]): (int(row[1]), int(row[2])) for row in rows}


def _summary_from_totals(total: int, errors_5xx: int) -> ApiAvailabilitySummary:
    return summary_from_totals(total, errors_5xx)


def compute_availability_from_db(db: Session) -> ApiAvailabilitySummary:
    since_epoch = _window_since_epoch()
    buckets = fetch_buckets(db, since_epoch)
    total = sum(values[0] for values in buckets.values())
    errors_5xx = sum(values[1] for values in buckets.values())
    return _summary_from_totals(total, errors_5xx)


def rollup_daily(
    buckets: dict[int, tuple[int, int]],
    *,
    target_percent: float | None = None,
) -> list[ApiSloDaySummary]:
    target = target_percent if target_percent is not None else api_slo_target_percent()
    target_ratio = target / 100.0
    by_day: dict[date, list[tuple[int, int]]] = {}

    for hour_epoch, (request_total, errors_5xx) in buckets.items():
        day = datetime.fromtimestamp(hour_epoch, tz=timezone.utc).date()
        by_day.setdefault(day, []).append((request_total, errors_5xx))

    items: list[ApiSloDaySummary] = []
    for day in sorted(by_day):
        totals = by_day[day]
        request_count = sum(item[0] for item in totals)
        errors = sum(item[1] for item in totals)
        if request_count == 0:
            items.append(
                ApiSloDaySummary(
                    day=day,
                    availability_ratio=None,
                    availability_percent=None,
                    request_count=0,
                    errors_5xx=0,
                    slo_ok=True,
                )
            )
            continue
        ratio = (request_count - errors) / request_count
        items.append(
            ApiSloDaySummary(
                day=day,
                availability_ratio=ratio,
                availability_percent=ratio * 100.0,
                request_count=request_count,
                errors_5xx=errors,
                slo_ok=ratio >= target_ratio,
            )
        )
    return items


def fetch_daily_history(db: Session, days: int) -> list[ApiSloDaySummary]:
    now = datetime.now(timezone.utc)
    start_day = (now - timedelta(days=days - 1)).date()
    start_epoch = int(
        datetime(start_day.year, start_day.month, start_day.day, tzinfo=timezone.utc).timestamp()
    )
    buckets = fetch_buckets(db, start_epoch)
    rolled = rollup_daily(buckets)
    rolled_by_day = {item.day: item for item in rolled}

    items: list[ApiSloDaySummary] = []
    for offset in range(days):
        day = start_day + timedelta(days=offset)
        items.append(
            rolled_by_day.get(
                day,
                ApiSloDaySummary(
                    day=day,
                    availability_ratio=None,
                    availability_percent=None,
                    request_count=0,
                    errors_5xx=0,
                    slo_ok=True,
                ),
            )
        )
    return items


def prune_old_buckets(db: Session) -> int:
    retention_days = slo_api_retention_days()
    cutoff_epoch = _current_bucket_epoch() - retention_days * 86400
    result = db.execute(
        delete(ApiSloHourlyBucket).where(ApiSloHourlyBucket.hour_epoch < cutoff_epoch)
    )
    fleet_result = db.execute(
        delete(ApiSloFleetHourlyBucket).where(ApiSloFleetHourlyBucket.hour_epoch < cutoff_epoch)
    )
    db.commit()
    return int((result.rowcount or 0) + (fleet_result.rowcount or 0))


def clear_buckets_for_tests(db: Session) -> None:
    db.execute(delete(ApiSloHourlyBucket))
    db.execute(delete(ApiSloFleetHourlyBucket))
    db.commit()


def upsert_fleet_hourly_bucket(
    db: Session,
    fleet_id: uuid.UUID,
    hour_epoch: int,
    *,
    inc_total: int = 0,
    inc_5xx: int = 0,
) -> None:
    now = datetime.now(timezone.utc)
    row = db.get(ApiSloFleetHourlyBucket, (fleet_id, hour_epoch))
    if row is None:
        db.add(
            ApiSloFleetHourlyBucket(
                fleet_id=fleet_id,
                hour_epoch=hour_epoch,
                request_total=inc_total,
                errors_5xx=inc_5xx,
                updated_at=now,
            )
        )
    else:
        row.request_total += inc_total
        row.errors_5xx += inc_5xx
        row.updated_at = now
    db.commit()


def fetch_fleet_buckets(
    db: Session,
    fleet_id: uuid.UUID,
    since_epoch: int,
) -> dict[int, tuple[int, int]]:
    rows = db.execute(
        select(
            ApiSloFleetHourlyBucket.hour_epoch,
            ApiSloFleetHourlyBucket.request_total,
            ApiSloFleetHourlyBucket.errors_5xx,
        ).where(
            ApiSloFleetHourlyBucket.fleet_id == fleet_id,
            ApiSloFleetHourlyBucket.hour_epoch >= since_epoch,
        )
    ).all()
    return {int(row[0]): (int(row[1]), int(row[2])) for row in rows}


def compute_fleet_availability_from_db(
    db: Session,
    fleet_id: uuid.UUID,
) -> ApiAvailabilitySummary:
    since_epoch = _window_since_epoch()
    buckets = fetch_fleet_buckets(db, fleet_id, since_epoch)
    total = sum(values[0] for values in buckets.values())
    errors_5xx = sum(values[1] for values in buckets.values())
    return _summary_from_totals(total, errors_5xx)


def fetch_fleet_daily_history(
    db: Session,
    fleet_id: uuid.UUID,
    days: int,
) -> list[ApiSloDaySummary]:
    now = datetime.now(timezone.utc)
    start_day = (now - timedelta(days=days - 1)).date()
    start_epoch = int(
        datetime(start_day.year, start_day.month, start_day.day, tzinfo=timezone.utc).timestamp()
    )
    buckets = fetch_fleet_buckets(db, fleet_id, start_epoch)
    rolled = rollup_daily(buckets)
    rolled_by_day = {item.day: item for item in rolled}

    items: list[ApiSloDaySummary] = []
    for offset in range(days):
        day = start_day + timedelta(days=offset)
        items.append(
            rolled_by_day.get(
                day,
                ApiSloDaySummary(
                    day=day,
                    availability_ratio=None,
                    availability_percent=None,
                    request_count=0,
                    errors_5xx=0,
                    slo_ok=True,
                ),
            )
        )
    return items


def list_distinct_fleet_ids(db: Session, since_epoch: int) -> list[uuid.UUID]:
    rows = db.execute(
        select(ApiSloFleetHourlyBucket.fleet_id)
        .where(ApiSloFleetHourlyBucket.hour_epoch >= since_epoch)
        .distinct()
    ).all()
    return [row[0] for row in rows]


def clear_fleet_buckets_for_tests(db: Session) -> None:
    db.execute(delete(ApiSloFleetHourlyBucket))
    db.commit()


def hydrate_memory_from_db(db: Session) -> None:
    global _hydrated
    since_epoch = _window_since_epoch()
    buckets = fetch_buckets(db, since_epoch)
    replace_memory_buckets(
        (hour_epoch, request_total, errors_5xx)
        for hour_epoch, (request_total, errors_5xx) in sorted(buckets.items())
    )
    _hydrated = True


def ensure_hydrated_and_pruned(db: Session) -> None:
    global _hydrated
    if not _hydrated:
        hydrate_memory_from_db(db)
    prune_old_buckets(db)


def reset_hydration_for_tests() -> None:
    global _hydrated
    _hydrated = False
