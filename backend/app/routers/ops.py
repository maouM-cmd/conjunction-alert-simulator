"""Ops dashboard REST API (Phase 9C)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.db.models import ConjunctionAlert
from backend.app.db.session import require_db
from backend.app.models.schemas import (
    AlertStatus,
    AlertTransition,
    ConjunctionAlertListOut,
    ConjunctionAlertOut,
    FleetOpsSummaryOut,
)
from backend.app.services import alert_service

router = APIRouter(prefix="/api/v1/ops", tags=["ops"])


def _parse_uuid(value: str, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"無効な {label} です。") from exc


def _handle_service_error(exc: alert_service.AlertServiceError) -> HTTPException:
    if isinstance(exc, alert_service.NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, alert_service.ValidationError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


def _alert_out(alert: ConjunctionAlert) -> ConjunctionAlertOut:
    sat = alert.satellite
    return ConjunctionAlertOut(
        id=str(alert.id),
        fleet_id=str(alert.fleet_id),
        satellite_id=str(alert.satellite_id),
        satellite_name=sat.name if sat else "UNKNOWN",
        satellite_norad_id=sat.norad_id if sat else 0,
        screening_run_id=str(alert.screening_run_id) if alert.screening_run_id else None,
        debris_norad_id=alert.debris_norad_id,
        debris_name=alert.debris_name,
        tca=alert.tca,
        pc=alert.pc,
        miss_distance_km=alert.miss_distance_km,
        risk_level=alert.risk_level,
        status=alert.status,  # type: ignore[arg-type]
        comment=alert.comment,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
    )


@router.get("/fleets/{fleet_id}/summary", response_model=FleetOpsSummaryOut)
def fleet_ops_summary(fleet_id: str, db: Session = Depends(require_db)) -> FleetOpsSummaryOut:
    fid = _parse_uuid(fleet_id, "fleet_id")
    try:
        summary = alert_service.get_fleet_summary(db, fid)
    except alert_service.AlertServiceError as exc:
        raise _handle_service_error(exc) from exc
    return FleetOpsSummaryOut(
        fleet_id=str(summary["fleet_id"]),
        fleet_name=summary["fleet_name"],
        open_count=summary["open_count"],
        acknowledged_count=summary["acknowledged_count"],
        mitigation_planned_count=summary["mitigation_planned_count"],
        closed_count=summary["closed_count"],
        false_positive_count=summary["false_positive_count"],
        latest_run_id=str(summary["latest_run_id"]) if summary["latest_run_id"] else None,
        latest_run_status=summary["latest_run_status"],
        latest_run_finished_at=summary["latest_run_finished_at"],
    )


@router.get("/alerts", response_model=ConjunctionAlertListOut)
def list_alerts(
    db: Session = Depends(require_db),
    fleet_id: str | None = None,
    status: AlertStatus | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> ConjunctionAlertListOut:
    fid = _parse_uuid(fleet_id, "fleet_id") if fleet_id else None
    items, total = alert_service.list_alerts(
        db, fleet_id=fid, status=status, limit=limit, offset=offset
    )
    return ConjunctionAlertListOut(
        items=[_alert_out(a) for a in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/alerts/{alert_id}", response_model=ConjunctionAlertOut)
def get_alert(alert_id: str, db: Session = Depends(require_db)) -> ConjunctionAlertOut:
    aid = _parse_uuid(alert_id, "alert_id")
    try:
        alert = alert_service.get_alert(db, aid)
    except alert_service.AlertServiceError as exc:
        raise _handle_service_error(exc) from exc
    return _alert_out(alert)


@router.patch("/alerts/{alert_id}", response_model=ConjunctionAlertOut)
def transition_alert(
    alert_id: str, body: AlertTransition, db: Session = Depends(require_db)
) -> ConjunctionAlertOut:
    aid = _parse_uuid(alert_id, "alert_id")
    try:
        alert = alert_service.transition_alert(
            db, aid, new_status=body.status, comment=body.comment
        )
    except alert_service.AlertServiceError as exc:
        raise _handle_service_error(exc) from exc
    return _alert_out(alert)
