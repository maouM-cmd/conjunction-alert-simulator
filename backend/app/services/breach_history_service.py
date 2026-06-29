"""Breach state transition history (Phase 10AC)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
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
):
    from backend.app.db.models import FleetAlertBreachHistory

    resolved = resolve_alertnames_filter(alertname, alertnames)
    if resolved is not None:
        base = base.where(FleetAlertBreachHistory.alertname.in_(resolved))
    if source is not None:
        base = base.where(FleetAlertBreachHistory.source == source)
    if breaching_only:
        base = base.where(FleetAlertBreachHistory.is_breaching.is_(True))
    return base


def list_history(
    db: Session,
    fleet_id: uuid.UUID,
    *,
    alertname: str | None = None,
    alertnames: list[str] | None = None,
    source: str | None = None,
    breaching_only: bool = False,
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
    )

    count_stmt = select(func.count()).select_from(base.subquery())
    total = db.execute(count_stmt).scalar_one()

    rows = db.execute(
        base.order_by(FleetAlertBreachHistory.created_at.desc()).limit(limit).offset(offset)
    ).scalars().unique().all()
    return list(rows), int(total)


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
