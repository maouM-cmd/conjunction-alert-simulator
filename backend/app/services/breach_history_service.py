"""Breach state transition history (Phase 10AC)."""

from __future__ import annotations

import csv
import io
import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import Session, joinedload

from backend.app.db.session import get_session_factory, is_database_configured

VALID_SOURCES = frozenset({"sync", "manual", "sticky_clear"})


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def breach_history_enabled() -> bool:
    return _env_bool("ALERTMANAGER_BREACH_HISTORY_ENABLED", default=False)


def breach_history_retention_days() -> int:
    raw = os.getenv("ALERTMANAGER_BREACH_HISTORY_RETENTION_DAYS", "90").strip()
    try:
        return max(int(raw), 1)
    except ValueError:
        return 90


RETENTION_DAYS_MIN = 1
RETENTION_DAYS_MAX = 3650
RETENTION_CSV_HEADER = ("fleet_id", "fleet_name", "retention_days", "effective_retention_days")


@dataclass(frozen=True)
class FleetRetentionRow:
    fleet_id: uuid.UUID
    fleet_name: str
    retention_days: int | None
    effective_retention_days: int


@dataclass(frozen=True)
class DaySummaryRow:
    day: date
    total: int
    breaching_count: int


@dataclass(frozen=True)
class FleetDaySummaryRow:
    day: date
    fleet_id: uuid.UUID
    fleet_name: str
    total: int
    breaching_count: int


def list_fleet_retention_settings(db: Session) -> list[FleetRetentionRow]:
    from backend.app.db.models import Fleet

    fleets = db.execute(
        select(Fleet).where(Fleet.active.is_(True)).order_by(Fleet.name)
    ).scalars().all()
    return [
        FleetRetentionRow(
            fleet_id=fleet.id,
            fleet_name=fleet.name,
            retention_days=fleet.breach_history_retention_days,
            effective_retention_days=effective_retention_days(db, fleet.id),
        )
        for fleet in fleets
    ]


def bulk_update_fleet_retention(
    db: Session,
    items: list[tuple[uuid.UUID, int | None]],
) -> int:
    updated = 0
    for fleet_id, retention_days in items:
        if retention_days is not None and not (
            RETENTION_DAYS_MIN <= retention_days <= RETENTION_DAYS_MAX
        ):
            raise ValueError("retention_days out of range")
        update_fleet_retention_days(db, fleet_id, retention_days)
        updated += 1
    return updated


def parse_retention_csv(content: str) -> list[tuple[uuid.UUID, int | None]]:
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        raise ValueError("CSV が空です。")
    header = tuple(cell.strip() for cell in rows[0])
    if header != RETENTION_CSV_HEADER:
        expected = ",".join(RETENTION_CSV_HEADER)
        raise ValueError(f"ヘッダー行が不正です。期待: {expected}")

    parsed: list[tuple[uuid.UUID, int | None]] = []
    for line_no, row in enumerate(rows[1:], start=2):
        if not row or all(not cell.strip() for cell in row):
            continue
        while len(row) < 4:
            row.append("")
        fleet_id_raw = row[0].strip()
        retention_raw = row[2].strip()
        try:
            fleet_id = uuid.UUID(fleet_id_raw)
        except ValueError as exc:
            raise ValueError(f"行 {line_no}: fleet_id が不正です。") from exc
        if retention_raw == "":
            retention_days = None
        else:
            try:
                retention_days = int(retention_raw)
            except ValueError as exc:
                raise ValueError(f"行 {line_no}: retention_days が不正です。") from exc
            if not (RETENTION_DAYS_MIN <= retention_days <= RETENTION_DAYS_MAX):
                raise ValueError(f"行 {line_no}: retention_days が範囲外です。")
        parsed.append((fleet_id, retention_days))
    if not parsed:
        raise ValueError("有効なデータ行がありません。")
    return parsed


def effective_retention_days(db: Session, fleet_id: uuid.UUID | None) -> int:
    if fleet_id is None:
        return breach_history_retention_days()
    from backend.app.db.models import Fleet

    fleet = db.get(Fleet, fleet_id)
    if fleet is not None and fleet.breach_history_retention_days is not None:
        return max(min(fleet.breach_history_retention_days, RETENTION_DAYS_MAX), RETENTION_DAYS_MIN)
    return breach_history_retention_days()


def update_fleet_retention_days(
    db: Session,
    fleet_id: uuid.UUID,
    retention_days: int | None,
) -> int:
    from backend.app.db.models import Fleet

    fleet = db.get(Fleet, fleet_id)
    if fleet is None or not fleet.active:
        raise ValueError("fleet not found")
    if retention_days is not None and not (RETENTION_DAYS_MIN <= retention_days <= RETENTION_DAYS_MAX):
        raise ValueError("retention_days out of range")
    fleet.breach_history_retention_days = retention_days
    db.commit()
    db.refresh(fleet)
    return effective_retention_days(db, fleet_id)


def resolve_alertnames_filter(
    alertname: str | None,
    alertnames: list[str] | None,
) -> list[str] | None:
    names: list[str] = []
    if alertnames:
        names.extend(alertnames)
    if alertname is not None:
        names.append(alertname)
    if not names:
        return None
    return list(dict.fromkeys(names))


def record_transition(
    fleet_id: uuid.UUID,
    alertname: str,
    is_breaching: bool,
    source: str,
    *,
    is_sticky: bool = False,
) -> None:
    if not breach_history_enabled():
        return
    if source not in VALID_SOURCES:
        return
    if not is_database_configured():
        return
    factory = get_session_factory()
    if factory is None:
        return

    from backend.app.db.models import FleetAlertBreachHistory

    db = factory()
    try:
        row = FleetAlertBreachHistory(
            fleet_id=fleet_id,
            alertname=alertname,
            is_breaching=is_breaching,
            source=source,
            is_sticky=is_sticky,
        )
        db.add(row)
        db.commit()
    finally:
        db.close()


def _apply_history_filters(
    base,
    *,
    alertname: str | None = None,
    alertnames: list[str] | None = None,
    source: str | None = None,
    breaching_only: bool = False,
    since: datetime | None = None,
    until: datetime | None = None,
):
    from backend.app.db.models import FleetAlertBreachHistory

    resolved = resolve_alertnames_filter(alertname, alertnames)
    if resolved is not None:
        base = base.where(FleetAlertBreachHistory.alertname.in_(resolved))
    if source is not None:
        base = base.where(FleetAlertBreachHistory.source == source)
    if breaching_only:
        base = base.where(FleetAlertBreachHistory.is_breaching.is_(True))
    if since is not None:
        base = base.where(FleetAlertBreachHistory.created_at >= since)
    if until is not None:
        base = base.where(FleetAlertBreachHistory.created_at <= until)
    return base


def list_history(
    db: Session,
    fleet_id: uuid.UUID,
    *,
    alertname: str | None = None,
    alertnames: list[str] | None = None,
    source: str | None = None,
    breaching_only: bool = False,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list, int]:
    from backend.app.db.models import FleetAlertBreachHistory

    base = select(FleetAlertBreachHistory).where(FleetAlertBreachHistory.fleet_id == fleet_id)
    base = _apply_history_filters(
        base,
        alertname=alertname,
        alertnames=alertnames,
        source=source,
        breaching_only=breaching_only,
        since=since,
        until=until,
    )

    count_stmt = select(func.count()).select_from(base.subquery())
    total = db.execute(count_stmt).scalar_one()

    rows = db.execute(
        base.order_by(FleetAlertBreachHistory.created_at.desc()).limit(limit).offset(offset)
    ).scalars().all()
    return list(rows), int(total)


def list_all_history(
    db: Session,
    *,
    alertname: str | None = None,
    alertnames: list[str] | None = None,
    source: str | None = None,
    breaching_only: bool = False,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list, int]:
    from backend.app.db.models import FleetAlertBreachHistory

    base = select(FleetAlertBreachHistory).options(joinedload(FleetAlertBreachHistory.fleet))
    base = _apply_history_filters(
        base,
        alertname=alertname,
        alertnames=alertnames,
        source=source,
        breaching_only=breaching_only,
        since=since,
        until=until,
    )

    count_stmt = select(func.count()).select_from(base.subquery())
    total = db.execute(count_stmt).scalar_one()

    rows = db.execute(
        base.order_by(FleetAlertBreachHistory.created_at.desc()).limit(limit).offset(offset)
    ).scalars().unique().all()
    return list(rows), int(total)


def _summarize_filtered(
    db: Session,
    *,
    fleet_id: uuid.UUID | None = None,
    alertname: str | None = None,
    alertnames: list[str] | None = None,
    source: str | None = None,
    breaching_only: bool = False,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[DaySummaryRow]:
    from backend.app.db.models import FleetAlertBreachHistory

    day_col = func.date(FleetAlertBreachHistory.created_at)
    stmt = select(
        day_col.label("day"),
        func.count().label("total"),
        func.sum(
            case((FleetAlertBreachHistory.is_breaching.is_(True), 1), else_=0)
        ).label("breaching_count"),
    ).select_from(FleetAlertBreachHistory)
    if fleet_id is not None:
        stmt = stmt.where(FleetAlertBreachHistory.fleet_id == fleet_id)
    stmt = _apply_history_filters(
        stmt,
        alertname=alertname,
        alertnames=alertnames,
        source=source,
        breaching_only=breaching_only,
        since=since,
        until=until,
    )
    stmt = stmt.group_by(day_col).order_by(day_col.desc())
    rows = db.execute(stmt).all()
    return [
        DaySummaryRow(
            day=row.day if isinstance(row.day, date) else date.fromisoformat(str(row.day)),
            total=int(row.total or 0),
            breaching_count=int(row.breaching_count or 0),
        )
        for row in rows
    ]


def summarize_history(
    db: Session,
    fleet_id: uuid.UUID,
    *,
    alertname: str | None = None,
    alertnames: list[str] | None = None,
    source: str | None = None,
    breaching_only: bool = False,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[DaySummaryRow]:
    return _summarize_filtered(
        db,
        fleet_id=fleet_id,
        alertname=alertname,
        alertnames=alertnames,
        source=source,
        breaching_only=breaching_only,
        since=since,
        until=until,
    )


def summarize_all_history(
    db: Session,
    *,
    alertname: str | None = None,
    alertnames: list[str] | None = None,
    source: str | None = None,
    breaching_only: bool = False,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[DaySummaryRow]:
    return _summarize_filtered(
        db,
        fleet_id=None,
        alertname=alertname,
        alertnames=alertnames,
        source=source,
        breaching_only=breaching_only,
        since=since,
        until=until,
    )


def _summarize_by_fleet_filtered(
    db: Session,
    *,
    alertname: str | None = None,
    alertnames: list[str] | None = None,
    source: str | None = None,
    breaching_only: bool = False,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[FleetDaySummaryRow]:
    from backend.app.db.models import Fleet, FleetAlertBreachHistory

    day_col = func.date(FleetAlertBreachHistory.created_at)
    stmt = (
        select(
            day_col.label("day"),
            FleetAlertBreachHistory.fleet_id.label("fleet_id"),
            Fleet.name.label("fleet_name"),
            func.count().label("total"),
            func.sum(
                case((FleetAlertBreachHistory.is_breaching.is_(True), 1), else_=0)
            ).label("breaching_count"),
        )
        .select_from(FleetAlertBreachHistory)
        .join(Fleet, FleetAlertBreachHistory.fleet_id == Fleet.id)
    )
    stmt = _apply_history_filters(
        stmt,
        alertname=alertname,
        alertnames=alertnames,
        source=source,
        breaching_only=breaching_only,
        since=since,
        until=until,
    )
    stmt = stmt.group_by(day_col, FleetAlertBreachHistory.fleet_id, Fleet.name).order_by(
        day_col.desc(),
        Fleet.name,
    )
    rows = db.execute(stmt).all()
    return [
        FleetDaySummaryRow(
            day=row.day if isinstance(row.day, date) else date.fromisoformat(str(row.day)),
            fleet_id=row.fleet_id,
            fleet_name=row.fleet_name,
            total=int(row.total or 0),
            breaching_count=int(row.breaching_count or 0),
        )
        for row in rows
    ]


def summarize_all_history_by_fleet(
    db: Session,
    *,
    alertname: str | None = None,
    alertnames: list[str] | None = None,
    source: str | None = None,
    breaching_only: bool = False,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[FleetDaySummaryRow]:
    return _summarize_by_fleet_filtered(
        db,
        alertname=alertname,
        alertnames=alertnames,
        source=source,
        breaching_only=breaching_only,
        since=since,
        until=until,
    )


def purge_old_breach_history(db: Session, *, fleet_id: uuid.UUID | None = None) -> int:
    if not breach_history_enabled():
        return 0
    from backend.app.db.models import FleetAlertBreachHistory

    days = effective_retention_days(db, fleet_id)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = delete(FleetAlertBreachHistory).where(FleetAlertBreachHistory.created_at < cutoff)
    if fleet_id is not None:
        stmt = stmt.where(FleetAlertBreachHistory.fleet_id == fleet_id)
    result = db.execute(stmt)
    db.commit()
    return int(result.rowcount or 0)


def clear_history_for_tests() -> None:
    if not is_database_configured():
        return
    factory = get_session_factory()
    if factory is None:
        return
    from backend.app.db.models import FleetAlertBreachHistory

    db = factory()
    try:
        for row in db.query(FleetAlertBreachHistory).all():
            db.delete(row)
        db.commit()
    finally:
        db.close()
