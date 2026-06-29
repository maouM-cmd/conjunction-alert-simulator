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


def list_history(
    db: Session,
    fleet_id: uuid.UUID,
    *,
    alertname: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list, int]:
    from backend.app.db.models import FleetAlertBreachHistory

    base = select(FleetAlertBreachHistory).where(FleetAlertBreachHistory.fleet_id == fleet_id)
    if alertname is not None:
        base = base.where(FleetAlertBreachHistory.alertname == alertname)

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
    limit: int = 100,
    offset: int = 0,
) -> tuple[list, int]:
    from backend.app.db.models import FleetAlertBreachHistory

    base = select(FleetAlertBreachHistory).options(joinedload(FleetAlertBreachHistory.fleet))
    if alertname is not None:
        base = base.where(FleetAlertBreachHistory.alertname == alertname)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = db.execute(count_stmt).scalar_one()

    rows = db.execute(
        base.order_by(FleetAlertBreachHistory.created_at.desc()).limit(limit).offset(offset)
    ).scalars().unique().all()
    return list(rows), int(total)


def purge_old_breach_history(db: Session) -> int:
    if not breach_history_enabled():
        return 0
    from backend.app.db.models import FleetAlertBreachHistory

    cutoff = datetime.now(timezone.utc) - timedelta(days=breach_history_retention_days())
    result = db.execute(
        delete(FleetAlertBreachHistory).where(FleetAlertBreachHistory.created_at < cutoff)
    )
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
