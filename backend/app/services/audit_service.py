"""Audit log persistence (Phase 9E)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.app.db.models import AuditLog


def audit_log_retention_days() -> int:
    raw = os.getenv("AUDIT_LOG_RETENTION_DAYS", "90").strip()
    try:
        return max(int(raw), 1)
    except ValueError:
        return 90


def log_audit(
    db: Session,
    *,
    fleet_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | None = None,
    api_key_id: uuid.UUID | None = None,
    detail: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        fleet_id=fleet_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        api_key_id=api_key_id,
        detail=detail or {},
    )
    db.add(entry)
    db.flush()
    return entry


def list_audit_logs(
    db: Session,
    *,
    fleet_id: uuid.UUID,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    filters = (AuditLog.fleet_id == fleet_id,)
    total = int(db.execute(select(func.count()).select_from(AuditLog).where(*filters)).scalar_one())
    items = list(
        db.execute(
            select(AuditLog)
            .where(*filters)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )
    return items, total


def purge_old_audit_logs(db: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=audit_log_retention_days())
    result = db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
    db.commit()
    return int(result.rowcount or 0)
