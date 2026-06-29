"""Ops dashboard REST API (Phase 9C)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.auth.api_key import AuthPrincipal, check_fleet_access, get_auth_principal, principal_scoped_fleet_id
from backend.app.db.models import AlertMitigationPreview, AlertPcRefinement, AuditLog, ConjunctionAlert, Fleet
from backend.app.db.session import require_db
from backend.app.services.auth_config import is_api_key_required
from backend.app.models.schemas import (
    AlertStatus,
    AlertStateMachineOut,
    AlertTransition,
    AlertmanagerSilenceCreate,
    AlertmanagerSilenceCreatedOut,
    AlertmanagerSilenceBulkDelete,
    AlertmanagerSilenceBulkDeletedOut,
    AlertmanagerSilenceDeletedOut,
    AlertmanagerSilenceListOut,
    AlertmanagerSilenceOut,
    AlertmanagerTestOut,
    ApiSloDayOut,
    ApiSloHistoryOut,
    AuditLogListOut,
    AuditLogOut,
    ConjunctionAlertListOut,
    ConjunctionAlertOut,
    FleetOpsSummaryOut,
    FleetAlertRulesOut,
    FleetBreachStateListOut,
    FleetBreachStateMultiListOut,
    FleetBreachStateEntryOut,
    FleetBreachStateOut,
    FleetBreachStateUpdate,
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
    alert_stm_service,
    alertmanager_push_service,
    alertmanager_silence_service,
    api_availability_service,
    breach_state_store,
    audit_service,
    fleet_alert_metrics_service,
    fleet_api_availability_service,
    mitigation_service,
    pc_refinement_service,
    sla_service,
    slo_persistence_service,
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
        trigger_source=preview.trigger_source,
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
        trigger_source=refinement.trigger_source,
        api_key_id=str(refinement.api_key_id) if refinement.api_key_id else None,
        created_at=refinement.created_at,
    )


def _alert_escalated(alert: ConjunctionAlert) -> bool:
    if not alert.pc_refinements:
        return False
    return pc_refinement_service.is_pc_escalated(alert.pc_refinements[0].pc_refined)


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
        escalated=_alert_escalated(alert),
        auto_mitigation_planned=mitigation_service.is_auto_mitigation_planned(alert),
        allowed_next_statuses=alert_stm_service.allowed_targets(alert.status),  # type: ignore[arg-type]
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
    fleet_api = fleet_api_availability_service.compute_fleet_api_availability(summary.fleet_id)
    return FleetSlaOut(
        fleet_id=str(summary.fleet_id),
        fleet_name=summary.fleet_name,
        has_active_schedule=summary.has_active_schedule,
        last_completed_run_at=summary.last_completed_run_at,
        screening_lag_seconds=summary.screening_lag_seconds,
        screening_lag_hours=summary.screening_lag_hours,
        screening_sla_ok=summary.screening_sla_ok,
        screening_sla_target_hours=summary.screening_sla_target_hours,
        fleet_api_availability_ratio=fleet_api.availability_ratio if fleet_api else None,
        fleet_api_availability_percent=fleet_api.availability_percent if fleet_api else None,
        fleet_api_slo_ok=fleet_api.slo_ok if fleet_api else None,
        fleet_api_request_count=fleet_api.request_count if fleet_api else None,
        fleet_api_errors_5xx=fleet_api.errors_5xx if fleet_api else None,
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
    elif not principal.is_admin:
        scoped = principal_scoped_fleet_id(principal)
        if scoped is None:
            raise HTTPException(status_code=401, detail="API Key が必要です。")
        items = [sla_service.compute_fleet_sla(db, scoped)]
    else:
        items = sla_service.list_fleet_sla_summaries(db)

    overdue = sum(1 for item in items if item.has_active_schedule and not item.screening_sla_ok)
    api_slo = api_availability_service.compute_api_availability()
    return SlaSummaryOut(
        items=[_fleet_sla_out(item) for item in items],
        overdue_count=overdue,
        screening_sla_target_hours=target_hours,
        api_availability_ratio=api_slo.availability_ratio,
        api_availability_percent=api_slo.availability_percent,
        api_slo_target_percent=api_slo.slo_target_percent,
        api_slo_ok=api_slo.slo_ok,
        api_sample_window_hours=api_slo.sample_window_hours,
        api_request_count=api_slo.request_count,
    )


@router.get("/sla/api-history", response_model=ApiSloHistoryOut)
def api_sla_history(
    days: int = Query(30, ge=1, le=90),
    fleet_id: str | None = None,
    db: Session = Depends(require_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> ApiSloHistoryOut:
    if is_api_key_required() and not principal.is_admin:
        raise HTTPException(status_code=403, detail="管理者権限が必要です。")

    target_percent = api_availability_service.api_slo_target_percent()
    scoped_fleet: uuid.UUID | None = None
    if fleet_id is not None:
        scoped_fleet = _parse_uuid(fleet_id, "fleet_id")
        check_fleet_access(principal, scoped_fleet)

    if scoped_fleet is not None and fleet_api_availability_service.fleet_api_slo_enabled():
        if slo_persistence_service.slo_api_persist_enabled():
            items = slo_persistence_service.fetch_fleet_daily_history(db, scoped_fleet, days)
        else:
            from datetime import date, datetime, timedelta, timezone

            now = datetime.now(timezone.utc)
            start_day = (now - timedelta(days=days - 1)).date()
            buckets: dict[int, tuple[int, int]] = {}
            window_seconds = int(api_availability_service.api_rolling_window_hours() * 3600.0)
            now_epoch = int(now.timestamp())
            cutoff = now_epoch - (now_epoch % 3600) - window_seconds
            for hour_epoch, request_total, errors_5xx in fleet_api_availability_service.load_fleet_memory_buckets(
                scoped_fleet
            ):
                if hour_epoch >= cutoff:
                    buckets[hour_epoch] = (request_total, errors_5xx)
            rolled = slo_persistence_service.rollup_daily(buckets, target_percent=target_percent)
            rolled_by_day = {item.day: item for item in rolled}
            items = []
            for offset in range(days):
                day = start_day + timedelta(days=offset)
                items.append(
                    rolled_by_day.get(
                        day,
                        slo_persistence_service.ApiSloDaySummary(
                            day=day,
                            availability_ratio=None,
                            availability_percent=None,
                            request_count=0,
                            errors_5xx=0,
                            slo_ok=True,
                        ),
                    )
                )
    elif slo_persistence_service.slo_api_persist_enabled():
        items = slo_persistence_service.fetch_daily_history(db, days)
    else:
        from datetime import date, datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        start_day = (now - timedelta(days=days - 1)).date()
        buckets: dict[int, tuple[int, int]] = {}
        window_seconds = int(api_availability_service.api_rolling_window_hours() * 3600.0)
        now_epoch = int(now.timestamp())
        cutoff = now_epoch - (now_epoch % 3600) - window_seconds
        for hour_epoch, request_total, errors_5xx in api_availability_service.load_memory_buckets():
            if hour_epoch >= cutoff:
                buckets[hour_epoch] = (request_total, errors_5xx)
        rolled = slo_persistence_service.rollup_daily(buckets, target_percent=target_percent)
        rolled_by_day = {item.day: item for item in rolled}
        items = []
        for offset in range(days):
            day = start_day + timedelta(days=offset)
            items.append(
                rolled_by_day.get(
                    day,
                    slo_persistence_service.ApiSloDaySummary(
                        day=day,
                        availability_ratio=None,
                        availability_percent=None,
                        request_count=0,
                        errors_5xx=0,
                        slo_ok=True,
                    ),
                )
            )

    return ApiSloHistoryOut(
        days=days,
        target_percent=target_percent,
        items=[
            ApiSloDayOut(
                day=item.day,
                availability_ratio=item.availability_ratio,
                availability_percent=item.availability_percent,
                request_count=item.request_count,
                errors_5xx=item.errors_5xx,
                slo_ok=item.slo_ok,
            )
            for item in items
        ],
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
        escalated_count=summary["escalated_count"],
        acknowledged_count=summary["acknowledged_count"],
        mitigation_planned_count=summary["mitigation_planned_count"],
        closed_count=summary["closed_count"],
        false_positive_count=summary["false_positive_count"],
        open_high_count=summary["open_high_count"],
        open_medium_count=summary["open_medium_count"],
        open_low_count=summary["open_low_count"],
        latest_run_id=str(summary["latest_run_id"]) if summary["latest_run_id"] else None,
        latest_run_status=summary["latest_run_status"],
        latest_run_finished_at=summary["latest_run_finished_at"],
    )


@router.get("/alerts/state-machine", response_model=AlertStateMachineOut)
def alert_state_machine(
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> AlertStateMachineOut:
    _ = principal
    payload = alert_stm_service.state_machine_payload()
    return AlertStateMachineOut(**payload)


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
            trigger_source=mitigation_service.TRIGGER_MANUAL,
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
            trigger_source=mitigation_service.TRIGGER_MANUAL,
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
            trigger_source=pc_refinement_service.TRIGGER_MANUAL,
        )
        pc_refinement_service.maybe_escalate_after_refine(db, refinement)
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


@router.get("/prometheus/fleet-alert-rules", response_model=FleetAlertRulesOut)
def fleet_alert_rules(
    fleet_id: str | None = None,
    format: str = Query("yaml", pattern="^(yaml|json)$"),
    db: Session = Depends(require_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> FleetAlertRulesOut:
    if not fleet_alert_metrics_service.fleet_alert_metrics_enabled():
        raise HTTPException(
            status_code=503,
            detail="Fleet alert metrics は無効です（FLEET_ALERT_METRICS_ENABLED）。",
        )

    fleets: list[Fleet]
    scoped_fleet: uuid.UUID | None = None
    if fleet_id is not None:
        scoped_fleet = _parse_uuid(fleet_id, "fleet_id")
        check_fleet_access(principal, scoped_fleet)
        fleet = db.get(Fleet, scoped_fleet)
        if fleet is None or not fleet.active:
            raise HTTPException(status_code=404, detail="艦隊が見つかりません。")
        fleets = [fleet]
    elif is_api_key_required() and not principal.is_admin:
        scoped = principal_scoped_fleet_id(principal)
        if scoped is None:
            raise HTTPException(status_code=401, detail="API Key が必要です。")
        check_fleet_access(principal, scoped)
        fleet = db.get(Fleet, scoped)
        if fleet is None or not fleet.active:
            raise HTTPException(status_code=404, detail="艦隊が見つかりません。")
        fleets = [fleet]
        scoped_fleet = scoped
    else:
        fleets = fleet_alert_metrics_service.list_active_fleets(db)

    rules: list = []
    for fleet in fleets:
        rules.extend(fleet_alert_metrics_service.render_fleet_alert_rules(fleet.id, fleet.name))

    fmt = format.lower()
    if fmt == "json":
        content = fleet_alert_metrics_service.render_fleet_alert_rules_json(rules)
    else:
        content = fleet_alert_metrics_service.render_fleet_alert_rules_yaml(rules)

    return FleetAlertRulesOut(
        format=fmt,
        fleet_id=str(scoped_fleet) if scoped_fleet is not None else None,
        content=content,
    )


@router.post("/prometheus/alertmanager/test", response_model=AlertmanagerTestOut)
def alertmanager_test_push(
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> AlertmanagerTestOut:
    if is_api_key_required() and not principal.is_admin:
        raise HTTPException(status_code=403, detail="管理者 API Key が必要です。")
    result = alertmanager_push_service.send_test_push()
    if not result.sent:
        raise HTTPException(status_code=503, detail=result.message)
    return AlertmanagerTestOut(sent=result.sent, message=result.message)


def _resolve_fleet_for_am_silence(
    principal: AuthPrincipal,
    fleet_id: str,
) -> uuid.UUID:
    fid = _parse_uuid(fleet_id, "fleet_id")
    check_fleet_access(principal, fid)
    return fid


def _silence_out(item: alertmanager_silence_service.SilenceItem) -> AlertmanagerSilenceOut:
    return AlertmanagerSilenceOut(
        silence_id=item.silence_id,
        fleet_id=item.fleet_id,
        alertname=item.alertname,
        starts_at=item.starts_at,
        ends_at=item.ends_at,
        comment=item.comment,
    )


def _fleet_breach_state_list_out(fleet_id: uuid.UUID) -> FleetBreachStateListOut:
    items = breach_state_store.list_fleet_breach_states(str(fleet_id))
    return FleetBreachStateListOut(
        fleet_id=str(fleet_id),
        backend=breach_state_store.breach_state_backend(),
        manual_override_enabled=breach_state_store.breach_manual_override_enabled(),
        items=[
            FleetBreachStateOut(alertname=item.alertname, is_breaching=item.is_breaching)
            for item in items
        ],
        total=len(items),
    )


@router.post("/prometheus/alertmanager/silences", response_model=AlertmanagerSilenceCreatedOut)
def create_alertmanager_silence(
    body: AlertmanagerSilenceCreate,
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> AlertmanagerSilenceCreatedOut:
    if is_api_key_required() and not principal.is_admin:
        scoped = principal_scoped_fleet_id(principal)
        if scoped is None:
            raise HTTPException(status_code=403, detail="管理者または艦隊 API Key が必要です。")
    fid = _resolve_fleet_for_am_silence(principal, body.fleet_id)
    if not alertmanager_silence_service.alertmanager_silences_configured():
        raise HTTPException(status_code=503, detail="Alertmanager silences は無効です。")
    result = alertmanager_silence_service.create_fleet_silence(
        fid,
        alertname=body.alertname,
        duration_hours=body.duration_hours,
        comment=body.comment,
    )
    if not result.ok or not result.silence_id:
        raise HTTPException(status_code=503, detail=result.message)
    return AlertmanagerSilenceCreatedOut(silence_id=result.silence_id, message=result.message)


@router.get(
    "/prometheus/alertmanager/breach-states",
    response_model=FleetBreachStateListOut | FleetBreachStateMultiListOut,
)
def list_fleet_breach_states(
    fleet_id: str | None = None,
    db: Session = Depends(require_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> FleetBreachStateListOut | FleetBreachStateMultiListOut:
    if not alertmanager_push_service.alertmanager_push_enabled():
        raise HTTPException(status_code=503, detail="Alertmanager push は無効です。")

    if fleet_id is None:
        if is_api_key_required() and not principal.is_admin:
            raise HTTPException(status_code=403, detail="管理者権限が必要です。")
        if not principal.is_admin:
            raise HTTPException(status_code=403, detail="管理者権限が必要です。")
        rows = breach_state_store.list_all_fleet_breach_states(db)
        return FleetBreachStateMultiListOut(
            backend=breach_state_store.breach_state_backend(),
            manual_override_enabled=breach_state_store.breach_manual_override_enabled(),
            items=[
                FleetBreachStateEntryOut(
                    fleet_id=row.fleet_id,
                    fleet_name=row.fleet_name,
                    alertname=row.alertname,
                    is_breaching=row.is_breaching,
                )
                for row in rows
            ],
            total=len(rows),
        )

    fid = _resolve_fleet_for_am_silence(principal, fleet_id)
    return _fleet_breach_state_list_out(fid)


@router.put(
    "/prometheus/alertmanager/breach-states",
    response_model=FleetBreachStateListOut,
)
def update_fleet_breach_state(
    body: FleetBreachStateUpdate,
    db: Session = Depends(require_db),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> FleetBreachStateListOut:
    if not alertmanager_push_service.alertmanager_push_enabled():
        raise HTTPException(status_code=503, detail="Alertmanager push は無効です。")
    if not breach_state_store.breach_manual_override_enabled():
        raise HTTPException(status_code=503, detail="breach 状態の手動上書きは無効です。")
    if not breach_state_store.is_valid_fleet_alertname(body.alertname):
        raise HTTPException(status_code=422, detail="alertname が不正です。")

    fid = _resolve_fleet_for_am_silence(principal, body.fleet_id)
    breach_state_store.set_breach_state(str(fid), body.alertname, body.is_breaching)
    audit_service.log_audit(
        db,
        fleet_id=fid,
        action="alert.breach_state_manual_override",
        resource_type="fleet",
        resource_id=fid,
        api_key_id=principal.api_key.id if principal.api_key else None,
        detail={
            "alertname": body.alertname,
            "is_breaching": body.is_breaching,
            "backend": breach_state_store.breach_state_backend(),
        },
    )
    db.commit()
    return _fleet_breach_state_list_out(fid)


@router.post(
    "/prometheus/alertmanager/silences/bulk-delete",
    response_model=AlertmanagerSilenceBulkDeletedOut,
)
def bulk_delete_alertmanager_silences_by_ids(
    body: AlertmanagerSilenceBulkDelete,
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> AlertmanagerSilenceBulkDeletedOut:
    if not alertmanager_silence_service.alertmanager_silences_configured():
        raise HTTPException(status_code=503, detail="Alertmanager silences は無効です。")

    if is_api_key_required() and not principal.is_admin:
        scoped = principal_scoped_fleet_id(principal)
        if scoped is None:
            raise HTTPException(status_code=403, detail="管理者または艦隊 API Key が必要です。")

    authorized_ids: list[str] = []
    not_found_ids: list[str] = []
    for silence_id in body.silence_ids:
        silence = alertmanager_silence_service.get_silence(silence_id)
        if silence is None:
            not_found_ids.append(silence_id)
            continue
        if silence.fleet_id is not None:
            _resolve_fleet_for_am_silence(principal, silence.fleet_id)
        authorized_ids.append(silence_id)

    if not authorized_ids:
        if not_found_ids:
            raise HTTPException(status_code=404, detail="silence が見つかりません。")
        raise HTTPException(status_code=404, detail="削除対象の silence がありません。")

    result = alertmanager_silence_service.delete_silences_by_ids(authorized_ids)
    if not result.ok:
        raise HTTPException(status_code=503, detail=result.message)
    return AlertmanagerSilenceBulkDeletedOut(
        deleted_count=result.deleted_count,
        silence_ids=list(result.silence_ids),
        message=result.message,
    )


@router.get("/prometheus/alertmanager/silences", response_model=AlertmanagerSilenceListOut)
def list_alertmanager_silences(
    fleet_id: str | None = None,
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> AlertmanagerSilenceListOut:
    if not alertmanager_silence_service.alertmanager_silences_configured():
        raise HTTPException(status_code=503, detail="Alertmanager silences は無効です。")

    scoped_fleet: uuid.UUID | None = None
    if fleet_id is not None:
        scoped_fleet = _resolve_fleet_for_am_silence(principal, fleet_id)
    elif is_api_key_required() and not principal.is_admin:
        scoped = principal_scoped_fleet_id(principal)
        if scoped is None:
            raise HTTPException(status_code=403, detail="管理者または艦隊 API Key が必要です。")
        scoped_fleet = scoped

    items, error = alertmanager_silence_service.list_silences(scoped_fleet)
    if error:
        raise HTTPException(status_code=503, detail=error)
    out = [_silence_out(item) for item in items]
    return AlertmanagerSilenceListOut(items=out, total=len(out))


@router.delete(
    "/prometheus/alertmanager/silences",
    response_model=AlertmanagerSilenceBulkDeletedOut,
)
def bulk_delete_alertmanager_silences(
    fleet_id: str = Query(...),
    alertname: str | None = None,
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> AlertmanagerSilenceBulkDeletedOut:
    if not alertmanager_silence_service.alertmanager_silences_configured():
        raise HTTPException(status_code=503, detail="Alertmanager silences は無効です。")

    if is_api_key_required() and not principal.is_admin:
        scoped = principal_scoped_fleet_id(principal)
        if scoped is None:
            raise HTTPException(status_code=403, detail="管理者または艦隊 API Key が必要です。")

    fid = _resolve_fleet_for_am_silence(principal, fleet_id)
    result = alertmanager_silence_service.delete_silences_for_fleet(fid, alertname=alertname)
    if not result.ok:
        raise HTTPException(status_code=503, detail=result.message)
    return AlertmanagerSilenceBulkDeletedOut(
        deleted_count=result.deleted_count,
        silence_ids=list(result.silence_ids),
        message=result.message,
    )


@router.delete(
    "/prometheus/alertmanager/silences/{silence_id}",
    response_model=AlertmanagerSilenceDeletedOut,
)
def delete_alertmanager_silence(
    silence_id: str,
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> AlertmanagerSilenceDeletedOut:
    if not alertmanager_silence_service.alertmanager_silences_configured():
        raise HTTPException(status_code=503, detail="Alertmanager silences は無効です。")

    if is_api_key_required() and not principal.is_admin:
        scoped = principal_scoped_fleet_id(principal)
        if scoped is None:
            raise HTTPException(status_code=403, detail="管理者または艦隊 API Key が必要です。")

    silence = alertmanager_silence_service.get_silence(silence_id)
    if silence is None:
        raise HTTPException(status_code=404, detail="silence が見つかりません。")

    if silence.fleet_id is not None:
        _resolve_fleet_for_am_silence(principal, silence.fleet_id)

    result = alertmanager_silence_service.delete_silence(silence_id)
    if not result.ok:
        raise HTTPException(status_code=503, detail=result.message)
    return AlertmanagerSilenceDeletedOut(silence_id=silence_id, message=result.message)


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
