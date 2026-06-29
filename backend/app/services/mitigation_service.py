"""Alert-linked maneuver preview (Phase 10A)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.app.db.models import AlertMitigationPreview, ConjunctionAlert
from backend.app.services.analysis import run_maneuver_preview
from backend.app.services.tle_fetcher import find_tle_by_norad_id


class MitigationServiceError(Exception):
    pass


class NotFoundError(MitigationServiceError):
    pass


def run_alert_mitigation_preview(
    db: Session,
    alert_id: uuid.UUID,
    *,
    direction: str = "prograde",
    delta_v_ms: float = 0.01,
    duration_days: float = 7.0,
    step_minutes: int = 1,
    api_key_id: uuid.UUID | None = None,
) -> AlertMitigationPreview:
    alert = db.execute(
        select(ConjunctionAlert)
        .options(joinedload(ConjunctionAlert.satellite))
        .where(ConjunctionAlert.id == alert_id)
    ).scalar_one_or_none()
    if alert is None:
        raise NotFoundError("アラートが見つかりません。")

    sat = alert.satellite
    if sat is None or not sat.tle:
        raise NotFoundError("衛星 TLE が見つかりません。")

    debris = find_tle_by_norad_id(alert.debris_norad_id)
    if debris is None:
        raise NotFoundError(
            f"デブリ NORAD {alert.debris_norad_id} の TLE が見つかりません。"
        )

    before, after = run_maneuver_preview(
        sat.tle,
        debris.text,
        direction,
        delta_v_ms,
        duration_days,
        step_minutes,
    )

    preview = AlertMitigationPreview(
        alert_id=alert.id,
        direction=direction,
        delta_v_ms=delta_v_ms,
        before_tca=before.tca,
        before_miss_distance_km=before.miss_distance_km,
        after_tca=after.tca,
        after_miss_distance_km=after.miss_distance_km,
        relative_velocity_kms=before.relative_velocity_kms,
        api_key_id=api_key_id,
    )
    db.add(preview)
    db.flush()

    from backend.app.services import audit_service

    audit_service.log_audit(
        db,
        fleet_id=alert.fleet_id,
        action="alert.mitigation_preview",
        resource_type="alert",
        resource_id=alert.id,
        api_key_id=api_key_id,
        detail={
            "preview_id": str(preview.id),
            "direction": direction,
            "delta_v_ms": delta_v_ms,
            "before_miss_km": before.miss_distance_km,
            "after_miss_km": after.miss_distance_km,
        },
    )
    db.commit()
    db.refresh(preview)
    return preview


def list_mitigation_previews(
    db: Session, alert_id: uuid.UUID
) -> list[AlertMitigationPreview]:
    alert = db.get(ConjunctionAlert, alert_id)
    if alert is None:
        raise NotFoundError("アラートが見つかりません。")
    return list(
        db.execute(
            select(AlertMitigationPreview)
            .where(AlertMitigationPreview.alert_id == alert_id)
            .order_by(AlertMitigationPreview.created_at.desc())
        )
        .scalars()
        .all()
    )
