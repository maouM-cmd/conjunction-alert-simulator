"""Ops dashboard REST API (Phase 9C)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.auth.api_key import AuthPrincipal, check_fleet_access, get_auth_principal
from backend.app.db.models import AuditLog, ConjunctionAlert
from backend.app.db.session import require_db
from backend.app.models.schemas import (
    AlertStatus,
    AlertTransition,
    AuditLogListOut,
    AuditLogOut,
    ConjunctionAlertListOut,
    ConjunctionAlertOut,
    FleetOpsSummaryOut,
)
from backend.app.services import alert_service, audit_service

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


def _audit_out(entry: AuditLog) -> AuditLogOut:
    return AuditLogOut(
        id=str(entry.id),
        fleet_id=str(entry.fleet_id) if entry.fleet_id else None,
        action=entry.action,
        resource_type=entry.resource_type,
        resource_id=str(entry.resource_id) if entry.resource_id else None,
        api_key_id=str(entry.api_key_id) if entry.api_key_id else None,
        detail=entry.detail or {},
        created_at=entry.created_at,
    )


@router.get("/fleets/{fleet_id}/summary", response_model=FleetOpsSummaryOut)
def fleet_ops_summary(
    fleet_id: str,
    db: Session = Depends(require_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> FleetOpsSummaryOut:
    fid = _parse_uuid(fleet_id, "fleet_id")
    check_fleet_access(principal, fid)
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
    principal: AuthPrincipal = Depends(get_auth_principal),
    fleet_id: str | None = None,
    status: AlertStatus | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> ConjunctionAlertListOut:
    if fleet_id is None:
        raise HTTPException(status_code=400, detail="fleet_id は必須です。")
    fid = _parse_uuid(fleet_id, "fleet_id")
    check_fleet_access(principal, fid)
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
def get_alert(
    alert_id: str,
    db: Session = Depends(require_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> ConjunctionAlertOut:
    aid = _parse_uuid(alert_id, "alert_id")
    try:
        alert = alert_service.get_alert(db, aid)
    except alert_service.AlertServiceError as exc:
        raise _handle_service_error(exc) from exc
    check_fleet_access(principal, alert.fleet_id)
    return _alert_out(alert)


@router.patch("/alerts/{alert_id}", response_model=ConjunctionAlertOut)
def transition_alert(
    alert_id: str,
    body: AlertTransition,
    db: Session = Depends(require_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> ConjunctionAlertOut:
    aid = _parse_uuid(alert_id, "alert_id")
    try:
        existing = alert_service.get_alert(db, aid)
        check_fleet_access(principal, existing.fleet_id)
        alert = alert_service.transition_alert(
            db,
            aid,
            new_status=body.status,
            comment=body.comment,
            api_key_id=principal.api_key.id if principal.api_key else None,
        )
    except alert_service.AlertServiceError as exc:
        raise _handle_service_error(exc) from exc
    return _alert_out(alert)


@router.get("/audit", response_model=AuditLogListOut)
def list_audit(
    db: Session = Depends(require_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
    fleet_id: str = Query(...),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> AuditLogListOut:
    fid = _parse_uuid(fleet_id, "fleet_id")
    check_fleet_access(principal, fid)
    items, total = audit_service.list_audit_logs(db, fleet_id=fid, limit=limit, offset=offset)
    return AuditLogListOut(
        items=[_audit_out(e) for e in items],
        total=total,
        limit=limit,
        offset=offset,
    )
