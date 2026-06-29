"""Conjunction alert persistence and triage."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from backend.app.db.models import ConjunctionAlert, Fleet, Satellite, ScreeningRun
from backend.app.services.alert_stm_service import ALL_ALERT_STATUSES, effective_allowed_transitions
from backend.app.services import fleet_alert_metrics_service
from backend.app.services.analysis import ConjunctionAnalysisResult
from backend.app.services.webhook_notifier import filter_alert_events

DEDUPE_WINDOW = timedelta(hours=24)

AlertStatus = str

class AlertServiceError(Exception):
    pass


class NotFoundError(AlertServiceError):
    pass


class ValidationError(AlertServiceError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _find_open_duplicate(
    db: Session,
    *,
    satellite_id: uuid.UUID,
    debris_norad_id: int,
    tca: datetime,
) -> ConjunctionAlert | None:
    tca = _ensure_aware(tca)
    window_start = tca - DEDUPE_WINDOW
    window_end = tca + DEDUPE_WINDOW
    candidates = (
        db.execute(
            select(ConjunctionAlert).where(
                ConjunctionAlert.satellite_id == satellite_id,
                ConjunctionAlert.debris_norad_id == debris_norad_id,
                ConjunctionAlert.status == "open",
                ConjunctionAlert.tca >= window_start,
                ConjunctionAlert.tca <= window_end,
            )
        )
        .scalars()
        .all()
    )
    return candidates[0] if candidates else None


def ingest_screening_results(
    db: Session,
    *,
    run_id: uuid.UUID,
    fleet_id: uuid.UUID,
    results: list[ConjunctionAnalysisResult],
    satellite_by_norad: dict[int, uuid.UUID],
) -> list[ConjunctionAlert]:
    """Persist alert events; return newly created open alerts for webhook."""
    new_opens: list[ConjunctionAlert] = []
    for result in results:
        satellite_id = satellite_by_norad.get(result.satellite.norad_id)
        if satellite_id is None:
            continue
        for event in filter_alert_events(result.events):
            existing = _find_open_duplicate(
                db,
                satellite_id=satellite_id,
                debris_norad_id=event.debris_norad_id,
                tca=event.tca,
            )
            if existing is not None:
                existing.tca = _ensure_aware(event.tca)
                existing.pc = event.pc
                existing.miss_distance_km = event.miss_distance_km
                existing.risk_level = event.risk_level
                existing.debris_name = event.debris_name
                existing.screening_run_id = run_id
                existing.updated_at = _utcnow()
                continue
            alert = ConjunctionAlert(
                fleet_id=fleet_id,
                satellite_id=satellite_id,
                screening_run_id=run_id,
                debris_norad_id=event.debris_norad_id,
                debris_name=event.debris_name,
                tca=_ensure_aware(event.tca),
                pc=event.pc,
                miss_distance_km=event.miss_distance_km,
                risk_level=event.risk_level,
                status="open",
            )
            db.add(alert)
            new_opens.append(alert)
    db.commit()
    for alert in new_opens:
        db.refresh(alert)
    return new_opens


def get_alert(db: Session, alert_id: uuid.UUID) -> ConjunctionAlert:
    alert = db.execute(
        select(ConjunctionAlert)
        .options(
            joinedload(ConjunctionAlert.satellite),
            selectinload(ConjunctionAlert.mitigation_previews),
            selectinload(ConjunctionAlert.pc_refinements),
        )
        .where(ConjunctionAlert.id == alert_id)
    ).scalar_one_or_none()
    if alert is None:
        raise NotFoundError("アラートが見つかりません。")
    return alert


def list_alerts(
    db: Session,
    *,
    fleet_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[ConjunctionAlert], int]:
    filters = []
    if fleet_id is not None:
        filters.append(ConjunctionAlert.fleet_id == fleet_id)
    if status is not None:
        filters.append(ConjunctionAlert.status == status)
    count_stmt = select(func.count()).select_from(ConjunctionAlert)
    list_stmt = select(ConjunctionAlert).options(
        joinedload(ConjunctionAlert.satellite),
        selectinload(ConjunctionAlert.mitigation_previews),
        selectinload(ConjunctionAlert.pc_refinements),
    )
    if filters:
        count_stmt = count_stmt.where(*filters)
        list_stmt = list_stmt.where(*filters)
    total = int(db.execute(count_stmt).scalar_one())
    items = list(
        db.execute(
            list_stmt.order_by(ConjunctionAlert.tca.desc()).limit(limit).offset(offset)
        )
        .scalars()
        .unique()
        .all()
    )
    return items, total


def transition_alert(
    db: Session,
    alert_id: uuid.UUID,
    *,
    new_status: str,
    comment: str | None = None,
    api_key_id: uuid.UUID | None = None,
    skip_pagerduty_outbound: bool = False,
) -> ConjunctionAlert:
    alert = get_alert(db, alert_id)
    allowed = effective_allowed_transitions().get(alert.status, set())
    if new_status not in allowed:
        raise ValidationError(
            f"状態 {alert.status} から {new_status} への遷移は許可されていません。"
        )
    old_status = alert.status
    alert.status = new_status
    if comment is not None:
        alert.comment = comment
    alert.updated_at = _utcnow()
    from backend.app.services import audit_service

    audit_service.log_audit(
        db,
        fleet_id=alert.fleet_id,
        action="alert.transition",
        resource_type="alert",
        resource_id=alert.id,
        api_key_id=api_key_id,
        detail={"from_status": old_status, "to_status": new_status, "comment": comment},
    )
    db.commit()
    db.refresh(alert)
    if not skip_pagerduty_outbound:
        from backend.app.services.webhook_notifier import notify_pagerduty_lifecycle_for_status

        notify_pagerduty_lifecycle_for_status(alert, new_status)
    return alert


def get_fleet_summary(db: Session, fleet_id: uuid.UUID) -> dict:
    fleet = db.get(Fleet, fleet_id)
    if fleet is None or not fleet.active:
        raise NotFoundError("艦隊が見つかりません。")

    counts: dict[str, int] = {}
    for status in ALL_ALERT_STATUSES:
        counts[status] = int(
            db.execute(
                select(func.count())
                .select_from(ConjunctionAlert)
                .where(ConjunctionAlert.fleet_id == fleet_id, ConjunctionAlert.status == status)
            ).scalar_one()
        )

    latest_run = db.execute(
        select(ScreeningRun)
        .where(ScreeningRun.fleet_id == fleet_id)
        .order_by(ScreeningRun.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    open_risk = fleet_alert_metrics_service.collect_open_risk_counts(db, fleet_id)

    return {
        "fleet_id": fleet_id,
        "fleet_name": fleet.name,
        "open_count": counts["open"],
        "escalated_count": counts["escalated"],
        "acknowledged_count": counts["acknowledged"],
        "mitigation_planned_count": counts["mitigation_planned"],
        "closed_count": counts["closed"],
        "false_positive_count": counts["false_positive"],
        "open_high_count": open_risk["high"],
        "open_medium_count": open_risk["medium"],
        "open_low_count": open_risk["low"],
        "latest_run_id": latest_run.id if latest_run else None,
        "latest_run_status": latest_run.status if latest_run else None,
        "latest_run_finished_at": latest_run.finished_at if latest_run else None,
    }
