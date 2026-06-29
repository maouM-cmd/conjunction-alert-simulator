"""Alert-linked maneuver preview (Phase 10A / 10C / 10F)."""

from __future__ import annotations

import os
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.app.db.models import AlertMitigationPreview, ConjunctionAlert
from backend.app.services.analysis import run_maneuver_preview
from backend.app.services.tle_fetcher import find_tle_by_norad_id
from backend.app.services.webhook_notifier import DEFAULT_PC_THRESHOLD

TRIGGER_MANUAL = "manual"
TRIGGER_SCREENING_AUTO = "screening_auto"

DEFAULT_SWEEP_DIRECTION = "prograde"
DEFAULT_SWEEP_MIN_MS = 0.01
DEFAULT_SWEEP_MAX_MS = 0.10
DEFAULT_SWEEP_STEP_MS = 0.01
DEFAULT_SWEEP_MAX_TRIALS = 20


class MitigationServiceError(Exception):
    pass


class NotFoundError(MitigationServiceError):
    pass


class ValidationError(MitigationServiceError):
    pass


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(float(raw), 0.0)
    except ValueError:
        return default


def auto_mitigation_sweep_enabled() -> bool:
    return _env_bool("AUTO_MITIGATION_SWEEP_ENABLED", default=False)


def auto_mitigation_sweep_on_escalation_only() -> bool:
    return _env_bool("AUTO_MITIGATION_SWEEP_ON_ESCALATION_ONLY", default=True)


def auto_mitigation_sweep_pc_min() -> float:
    return _env_float("AUTO_MITIGATION_SWEEP_PC_MIN", DEFAULT_PC_THRESHOLD)


def auto_mitigation_plan_enabled() -> bool:
    return _env_bool("AUTO_MITIGATION_PLAN_ENABLED", default=False)


def auto_ack_before_mitigation_plan() -> bool:
    return _env_bool("AUTO_ACK_BEFORE_MITIGATION_PLAN", default=False)


def is_improving_best(best: AlertMitigationPreview | None) -> bool:
    if best is None:
        return False
    return best.after_miss_distance_km > best.before_miss_distance_km


def is_auto_mitigation_planned(alert: ConjunctionAlert) -> bool:
    if alert.status != "mitigation_planned":
        return False
    if not alert.mitigation_previews:
        return False
    latest = alert.mitigation_previews[0]
    return latest.trigger_source == TRIGGER_SCREENING_AUTO


def should_auto_mitigation_sweep(
    *,
    escalated: bool,
    pc_refined: float | None,
) -> bool:
    if not auto_mitigation_sweep_enabled():
        return False
    if auto_mitigation_sweep_on_escalation_only():
        return escalated
    if pc_refined is None:
        return False
    return pc_refined >= auto_mitigation_sweep_pc_min()


def enqueue_auto_mitigation_sweep(
    alert_id: uuid.UUID,
    *,
    escalated: bool,
    pc_refined: float | None,
) -> bool:
    if not should_auto_mitigation_sweep(escalated=escalated, pc_refined=pc_refined):
        return False
    from backend.app.tasks.mitigation_tasks import mitigation_sweep_task

    mitigation_sweep_task.delay(str(alert_id))
    return True


def _load_alert_context(db: Session, alert_id: uuid.UUID) -> tuple[ConjunctionAlert, str]:
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
    return alert, debris.text


def _build_preview_row(
    alert: ConjunctionAlert,
    *,
    direction: str,
    delta_v_ms: float,
    duration_days: float,
    step_minutes: int,
    satellite_tle: str,
    debris_tle: str,
    api_key_id: uuid.UUID | None,
    trigger_source: str = TRIGGER_MANUAL,
) -> AlertMitigationPreview:
    before, after = run_maneuver_preview(
        satellite_tle,
        debris_tle,
        direction,
        delta_v_ms,
        duration_days,
        step_minutes,
    )
    return AlertMitigationPreview(
        alert_id=alert.id,
        direction=direction,
        delta_v_ms=delta_v_ms,
        before_tca=before.tca,
        before_miss_distance_km=before.miss_distance_km,
        after_tca=after.tca,
        after_miss_distance_km=after.miss_distance_km,
        relative_velocity_kms=before.relative_velocity_kms,
        trigger_source=trigger_source,
        api_key_id=api_key_id,
    )


def select_best_preview(
    previews: list[AlertMitigationPreview],
) -> AlertMitigationPreview | None:
    if not previews:
        return None
    improving = [
        p for p in previews if p.after_miss_distance_km > p.before_miss_distance_km
    ]
    if improving:
        return min(improving, key=lambda p: p.delta_v_ms)
    return max(previews, key=lambda p: p.after_miss_distance_km)


def _delta_v_series(
    *,
    delta_v_min_ms: float,
    delta_v_max_ms: float,
    delta_v_step_ms: float,
    max_trials: int,
) -> list[float]:
    if delta_v_step_ms <= 0:
        raise ValidationError("delta_v_step_ms は正の値である必要があります。")
    if delta_v_max_ms < delta_v_min_ms:
        raise ValidationError("delta_v_max_ms は delta_v_min_ms 以上である必要があります。")

    values: list[float] = []
    current = delta_v_min_ms
    while current <= delta_v_max_ms + 1e-12 and len(values) < max_trials:
        values.append(round(current, 6))
        current += delta_v_step_ms
    if not values:
        values.append(delta_v_min_ms)
    return values


def preview_comment_line(preview: AlertMitigationPreview) -> str:
    return (
        f"preview {preview.id}: Δv {preview.delta_v_ms} m/s ({preview.direction}), "
        f"miss {preview.before_miss_distance_km:.3f}→{preview.after_miss_distance_km:.3f} km"
    )


def run_alert_mitigation_preview(
    db: Session,
    alert_id: uuid.UUID,
    *,
    direction: str = "prograde",
    delta_v_ms: float = 0.01,
    duration_days: float = 7.0,
    step_minutes: int = 1,
    api_key_id: uuid.UUID | None = None,
    trigger_source: str = TRIGGER_MANUAL,
) -> AlertMitigationPreview:
    alert, debris_tle = _load_alert_context(db, alert_id)
    sat = alert.satellite
    assert sat is not None

    preview = _build_preview_row(
        alert,
        direction=direction,
        delta_v_ms=delta_v_ms,
        duration_days=duration_days,
        step_minutes=step_minutes,
        satellite_tle=sat.tle,
        debris_tle=debris_tle,
        api_key_id=api_key_id,
        trigger_source=trigger_source,
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
            "before_miss_km": preview.before_miss_distance_km,
            "after_miss_km": preview.after_miss_distance_km,
            "trigger_source": trigger_source,
        },
    )
    db.commit()
    db.refresh(preview)
    return preview


def run_alert_mitigation_sweep(
    db: Session,
    alert_id: uuid.UUID,
    *,
    direction: str = DEFAULT_SWEEP_DIRECTION,
    delta_v_min_ms: float = DEFAULT_SWEEP_MIN_MS,
    delta_v_max_ms: float = DEFAULT_SWEEP_MAX_MS,
    delta_v_step_ms: float = DEFAULT_SWEEP_STEP_MS,
    max_trials: int = DEFAULT_SWEEP_MAX_TRIALS,
    duration_days: float = 7.0,
    step_minutes: int = 1,
    api_key_id: uuid.UUID | None = None,
    trigger_source: str = TRIGGER_MANUAL,
) -> tuple[list[AlertMitigationPreview], AlertMitigationPreview | None]:
    alert, debris_tle = _load_alert_context(db, alert_id)
    sat = alert.satellite
    assert sat is not None

    delta_values = _delta_v_series(
        delta_v_min_ms=delta_v_min_ms,
        delta_v_max_ms=delta_v_max_ms,
        delta_v_step_ms=delta_v_step_ms,
        max_trials=max_trials,
    )

    previews: list[AlertMitigationPreview] = []
    for delta_v_ms in delta_values:
        preview = _build_preview_row(
            alert,
            direction=direction,
            delta_v_ms=delta_v_ms,
            duration_days=duration_days,
            step_minutes=step_minutes,
            satellite_tle=sat.tle,
            debris_tle=debris_tle,
            api_key_id=api_key_id,
            trigger_source=trigger_source,
        )
        db.add(preview)
        previews.append(preview)

    db.flush()
    best = select_best_preview(previews)

    from backend.app.services import audit_service

    audit_action = (
        "alert.mitigation_sweep_auto"
        if trigger_source == TRIGGER_SCREENING_AUTO
        else "alert.mitigation_sweep"
    )
    audit_service.log_audit(
        db,
        fleet_id=alert.fleet_id,
        action=audit_action,
        resource_type="alert",
        resource_id=alert.id,
        api_key_id=api_key_id,
        detail={
            "trial_count": len(previews),
            "best_preview_id": str(best.id) if best else None,
            "delta_v_min_ms": delta_v_min_ms,
            "delta_v_max_ms": delta_v_max_ms,
            "delta_v_step_ms": delta_v_step_ms,
            "direction": direction,
            "trigger_source": trigger_source,
        },
    )
    db.commit()
    for preview in previews:
        db.refresh(preview)
    return previews, best


def maybe_notify_mitigation_best(
    db: Session,
    alert_id: uuid.UUID,
    best: AlertMitigationPreview | None,
) -> bool:
    if best is None:
        return False

    alert = db.execute(
        select(ConjunctionAlert)
        .options(joinedload(ConjunctionAlert.satellite))
        .where(ConjunctionAlert.id == alert_id)
    ).scalar_one_or_none()
    if alert is None:
        return False

    from backend.app.services.webhook_notifier import notify_mitigation_best

    result = notify_mitigation_best(alert, best)
    return result.sent


def maybe_auto_mitigation_plan(
    db: Session,
    alert_id: uuid.UUID,
    best: AlertMitigationPreview | None,
) -> ConjunctionAlert | None:
    if not auto_mitigation_plan_enabled() or not is_improving_best(best):
        return None

    alert = db.execute(
        select(ConjunctionAlert)
        .options(joinedload(ConjunctionAlert.satellite))
        .where(ConjunctionAlert.id == alert_id)
    ).scalar_one_or_none()
    if alert is None or best is None:
        return None

    auto_ack = False
    if alert.status == "open" and auto_ack_before_mitigation_plan():
        from backend.app.services import alert_service

        alert = alert_service.transition_alert(
            db,
            alert_id,
            new_status="acknowledged",
            comment="auto-ack before mitigation plan",
            api_key_id=None,
        )
        auto_ack = True

    if alert.status != "acknowledged":
        return None

    updated = transition_alert_with_preview(
        db,
        alert_id,
        preview_id=best.id,
        comment="[auto mitigation plan]",
        api_key_id=None,
    )

    from backend.app.services import alert_service, audit_service
    from backend.app.services.webhook_notifier import notify_mitigation_plan_auto

    audit_service.log_audit(
        db,
        fleet_id=updated.fleet_id,
        action="alert.mitigation_plan_auto",
        resource_type="alert",
        resource_id=updated.id,
        api_key_id=None,
        detail={
            "preview_id": str(best.id),
            "delta_v_ms": best.delta_v_ms,
            "direction": best.direction,
            "auto_ack": auto_ack,
            "trigger_source": best.trigger_source,
        },
    )
    db.commit()
    notify_alert = alert_service.get_alert(db, alert_id)
    notify_mitigation_plan_auto(notify_alert, best)
    return notify_alert


def transition_alert_with_preview(
    db: Session,
    alert_id: uuid.UUID,
    *,
    preview_id: uuid.UUID | None = None,
    comment: str | None = None,
    api_key_id: uuid.UUID | None = None,
) -> ConjunctionAlert:
    alert = db.get(ConjunctionAlert, alert_id)
    if alert is None:
        raise NotFoundError("アラートが見つかりません。")

    if preview_id is not None:
        preview = db.get(AlertMitigationPreview, preview_id)
        if preview is None or preview.alert_id != alert_id:
            raise NotFoundError("試算結果が見つかりません。")
    else:
        previews = list_mitigation_previews(db, alert_id)
        if not previews:
            raise ValidationError("試算結果がありません。先に回避試算を実行してください。")
        preview = previews[0]

    if alert.status != "acknowledged":
        raise ValidationError(
            "対策計画への遷移は acknowledged 状態のアラートのみ可能です。"
        )

    auto_line = preview_comment_line(preview)
    full_comment = f"{auto_line}\n{comment}".strip() if comment else auto_line

    from backend.app.services import alert_service, audit_service

    updated = alert_service.transition_alert(
        db,
        alert_id,
        new_status="mitigation_planned",
        comment=full_comment,
        api_key_id=api_key_id,
    )
    audit_service.log_audit(
        db,
        fleet_id=alert.fleet_id,
        action="alert.mitigation_plan",
        resource_type="alert",
        resource_id=alert.id,
        api_key_id=api_key_id,
        detail={
            "preview_id": str(preview.id),
            "delta_v_ms": preview.delta_v_ms,
            "direction": preview.direction,
            "comment": full_comment,
        },
    )
    db.commit()
    db.refresh(updated)
    return updated


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
