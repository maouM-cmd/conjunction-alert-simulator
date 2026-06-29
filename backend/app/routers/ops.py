"""Ops dashboard REST API (Phase 9C)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.auth.api_key import AuthPrincipal, check_fleet_access, get_auth_principal
from backend.app.db.models import AlertMitigationPreview, AlertPcRefinement, AuditLog, ConjunctionAlert
from backend.app.db.session import require_db
from backend.app.models.schemas import (
    AlertStatus,
    AlertTransition,
    AuditLogListOut,
    AuditLogOut,
    ConjunctionAlertListOut,
    ConjunctionAlertOut,
    FleetOpsSummaryOut,
    FleetSlaOut,
    MitigationPreviewListOut,
    MitigationPreviewOut,
    MitigationPreviewRequest,
    MitigationPlanRequest,
    MitigationSweepOut,
    MitigationSweepRequest,
    PcRefinementListOut,
    PcRefinementOut,
    SlaSummaryOut,
)
from backend.app.services import (
    alert_service,
    audit_service,
    mitigation_service,
    pc_refinement_service,
    sla_service,
)

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


def _handle_mitigation_error(exc: mitigation_service.MitigationServiceError) -> HTTPException:
    if isinstance(exc, mitigation_service.NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, mitigation_service.ValidationError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


def _handle_pc_refinement_error(exc: pc_refinement_service.PcRefinementServiceError) -> HTTPException:
    if isinstance(exc, pc_refinement_service.NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


def _preview_out(preview: AlertMitigationPreview) -> MitigationPreviewOut:
    return MitigationPreviewOut(
        id=str(preview.id),
        alert_id=str(preview.alert_id),
        direction=preview.direction,
        delta_v_ms=preview.delta_v_ms,
        before_tca=preview.before_tca,
        before_miss_distance_km=preview.before_miss_distance_km,
        after_tca=preview.after_tca,
        after_miss_distance_km=preview.after_miss_distance_km,
        relative_velocity_kms=preview.relative_velocity_kms,
        api_key_id=str(preview.api_key_id) if preview.api_key_id else None,
        created_at=preview.created_at,
    )


def _latest_preview_out(alert: ConjunctionAlert) -> MitigationPreviewOut | None:
    if not alert.mitigation_previews:
        return None
    return _preview_out(alert.mitigation_previews[0])


def _pc_refinement_out(refinement: AlertPcRefinement) -> PcRefinementOut:
    return PcRefinementOut(
        id=str(refinement.id),
        alert_id=str(refinement.alert_id),
        pc_screening=refinement.pc_screening,
        pc_refined=refinement.pc_refined,
        pc_method=refinement.pc_method,
        covariance_source=refinement.covariance_source,
        miss_distance_km=refinement.miss_distance_km,
        api_key_id=str(refinement.api_key_id) if refinement.api_key_id else None,
        created_at=refinement.created_at,
    )


def _latest_pc_refinement_out(alert: ConjunctionAlert) -> PcRefinementOut | None:
    if not alert.pc_refinements:
        return None
    return _pc_refinement_out(alert.pc_refinements[0])


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
        latest_mitigation_preview=_latest_preview_out(alert),
        latest_pc_refinement=_latest_pc_refinement_out(alert),
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


def _fleet_sla_out(summary: sla_service.FleetSlaSummary) -> FleetSlaOut:
    return FleetSlaOut(
        fleet_id=str(summary.fleet_id),
        fleet_name=summary.fleet_name,
        has_active_schedule=summary.has_active_schedule,
        last_completed_run_at=summary.last_completed_run_at,
        screening_lag_seconds=summary.screening_lag_seconds,
        screening_lag_hours=summary.screening_lag_hours,
        screening_sla_ok=summary.screening_sla_ok,
        screening_sla_target_hours=summary.screening_sla_target_hours,
    )


@router.get("/sla", response_model=SlaSummaryOut)
def list_sla(
    db: Session = Depends(require_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
    fleet_id: str | None = None,
) -> SlaSummaryOut:
    target_hours = sla_service.screening_max_lag_hours()
    if fleet_id is not None:
        fid = _parse_uuid(fleet_id, "fleet_id")
        check_fleet_access(principal, fid)
        try:
            items = [sla_service.compute_fleet_sla(db, fid)]
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    elif principal.api_key is not None and not principal.is_admin:
        items = [sla_service.compute_fleet_sla(db, principal.api_key.fleet_id)]
    else:
        items = sla_service.list_fleet_sla_summaries(db)

    overdue = sum(1 for item in items if item.has_active_schedule and not item.screening_sla_ok)
    return SlaSummaryOut(
        items=[_fleet_sla_out(item) for item in items],
        overdue_count=overdue,
        screening_sla_target_hours=target_hours,
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


@router.post(
    "/alerts/{alert_id}/mitigation-preview",
    response_model=MitigationPreviewOut,
    status_code=201,
)
def create_mitigation_preview(
    alert_id: str,
    body: MitigationPreviewRequest,
    db: Session = Depends(require_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> MitigationPreviewOut:
    aid = _parse_uuid(alert_id, "alert_id")
    try:
        alert = alert_service.get_alert(db, aid)
        check_fleet_access(principal, alert.fleet_id)
        preview = mitigation_service.run_alert_mitigation_preview(
            db,
            aid,
            direction=body.direction,
            delta_v_ms=body.delta_v_ms,
            duration_days=body.duration_days,
            step_minutes=body.step_minutes,
            api_key_id=principal.api_key.id if principal.api_key else None,
        )
    except alert_service.AlertServiceError as exc:
        raise _handle_service_error(exc) from exc
    except mitigation_service.MitigationServiceError as exc:
        raise _handle_mitigation_error(exc) from exc
    return _preview_out(preview)


@router.get(
    "/alerts/{alert_id}/mitigation-previews",
    response_model=MitigationPreviewListOut,
)
def list_mitigation_previews(
    alert_id: str,
    db: Session = Depends(require_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> MitigationPreviewListOut:
    aid = _parse_uuid(alert_id, "alert_id")
    try:
        alert = alert_service.get_alert(db, aid)
        check_fleet_access(principal, alert.fleet_id)
        items = mitigation_service.list_mitigation_previews(db, aid)
    except alert_service.AlertServiceError as exc:
        raise _handle_service_error(exc) from exc
    except mitigation_service.MitigationServiceError as exc:
        raise _handle_mitigation_error(exc) from exc
    return MitigationPreviewListOut(
        items=[_preview_out(p) for p in items],
        total=len(items),
    )


@router.post(
    "/alerts/{alert_id}/mitigation-sweep",
    response_model=MitigationSweepOut,
    status_code=201,
)
def create_mitigation_sweep(
    alert_id: str,
    body: MitigationSweepRequest,
    db: Session = Depends(require_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> MitigationSweepOut:
    aid = _parse_uuid(alert_id, "alert_id")
    try:
        alert = alert_service.get_alert(db, aid)
        check_fleet_access(principal, alert.fleet_id)
        previews, best = mitigation_service.run_alert_mitigation_sweep(
            db,
            aid,
            direction=body.direction,
            delta_v_min_ms=body.delta_v_min_ms,
            delta_v_max_ms=body.delta_v_max_ms,
            delta_v_step_ms=body.delta_v_step_ms,
            max_trials=body.max_trials,
            duration_days=body.duration_days,
            step_minutes=body.step_minutes,
            api_key_id=principal.api_key.id if principal.api_key else None,
        )
    except alert_service.AlertServiceError as exc:
        raise _handle_service_error(exc) from exc
    except mitigation_service.MitigationServiceError as exc:
        raise _handle_mitigation_error(exc) from exc
    return MitigationSweepOut(
        items=[_preview_out(p) for p in previews],
        best=_preview_out(best) if best else None,
        total=len(previews),
    )


@router.post("/alerts/{alert_id}/mitigation-plan", response_model=ConjunctionAlertOut)
def create_mitigation_plan(
    alert_id: str,
    body: MitigationPlanRequest,
    db: Session = Depends(require_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> ConjunctionAlertOut:
    aid = _parse_uuid(alert_id, "alert_id")
    preview_uuid = None
    if body.preview_id is not None:
        preview_uuid = _parse_uuid(body.preview_id, "preview_id")
    try:
        alert = alert_service.get_alert(db, aid)
        check_fleet_access(principal, alert.fleet_id)
        updated = mitigation_service.transition_alert_with_preview(
            db,
            aid,
            preview_id=preview_uuid,
            comment=body.comment,
            api_key_id=principal.api_key.id if principal.api_key else None,
        )
    except alert_service.AlertServiceError as exc:
        raise _handle_service_error(exc) from exc
    except mitigation_service.MitigationServiceError as exc:
        raise _handle_mitigation_error(exc) from exc
    refreshed = alert_service.get_alert(db, updated.id)
    return _alert_out(refreshed)


@router.post(
    "/alerts/{alert_id}/pc-refine",
    response_model=PcRefinementOut,
    status_code=201,
)
def create_pc_refinement(
    alert_id: str,
    db: Session = Depends(require_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> PcRefinementOut:
    aid = _parse_uuid(alert_id, "alert_id")
    try:
        alert = alert_service.get_alert(db, aid)
        check_fleet_access(principal, alert.fleet_id)
        refinement = pc_refinement_service.refine_alert_pc(
            db,
            aid,
            api_key_id=principal.api_key.id if principal.api_key else None,
        )
    except alert_service.AlertServiceError as exc:
        raise _handle_service_error(exc) from exc
    except pc_refinement_service.PcRefinementServiceError as exc:
        raise _handle_pc_refinement_error(exc) from exc
    return _pc_refinement_out(refinement)


@router.get(
    "/alerts/{alert_id}/pc-refinements",
    response_model=PcRefinementListOut,
)
def list_pc_refinements(
    alert_id: str,
    db: Session = Depends(require_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> PcRefinementListOut:
    aid = _parse_uuid(alert_id, "alert_id")
    try:
        alert = alert_service.get_alert(db, aid)
        check_fleet_access(principal, alert.fleet_id)
        items = pc_refinement_service.list_pc_refinements(db, aid)
    except alert_service.AlertServiceError as exc:
        raise _handle_service_error(exc) from exc
    except pc_refinement_service.PcRefinementServiceError as exc:
        raise _handle_pc_refinement_error(exc) from exc
    return PcRefinementListOut(
        items=[_pc_refinement_out(r) for r in items],
        total=len(items),
    )


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
