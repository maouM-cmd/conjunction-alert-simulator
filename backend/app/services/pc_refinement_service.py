"""Alert-linked Pc refinement with CDM/TLE RTN covariance (Phase 10D)."""

from __future__ import annotations

import uuid
from datetime import timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.app.db.models import AlertPcRefinement, ConjunctionAlert
from backend.app.services.cdm_spacetrack_merge import apply_spacetrack_cdm_to_events
from backend.app.services.conjunction import ConjunctionEvent, find_closest_approach
from backend.app.services.pc_conjunction import pc_for_tle_pair_at_index
from backend.app.services.propagator import propagate_orbit
from backend.app.services.tle_fetcher import find_tle_by_norad_id
from backend.app.services.tle_parser import parse_tle

REFINE_WINDOW_HOURS = 1.0
REFINE_STEP_MINUTES = 1
DEFAULT_THRESHOLD_KM = 50.0


class PcRefinementServiceError(Exception):
    pass


class NotFoundError(PcRefinementServiceError):
    pass


def _ensure_aware(dt):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _find_tca_index(sat_pts, deb_pts, target_tca) -> int:
    target = _ensure_aware(target_tca)
    best_idx = 0
    best_delta = None
    n = min(len(sat_pts), len(deb_pts))
    for i in range(n):
        delta = abs((_ensure_aware(sat_pts[i].time) - target).total_seconds())
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_idx = i
    return best_idx


def _synthetic_event(alert: ConjunctionAlert, debris_tle: str, tca_index: int) -> ConjunctionEvent:
    return ConjunctionEvent(
        debris_norad_id=alert.debris_norad_id,
        debris_name=alert.debris_name,
        debris_tle=debris_tle,
        tca=_ensure_aware(alert.tca),
        miss_distance_km=alert.miss_distance_km,
        relative_velocity_kms=0.0,
        risk_level=alert.risk_level,
        pc=alert.pc,
        tca_index=tca_index,
    )


def refine_alert_pc(
    db: Session,
    alert_id: uuid.UUID,
    *,
    api_key_id: uuid.UUID | None = None,
) -> AlertPcRefinement:
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

    debris_parsed = find_tle_by_norad_id(alert.debris_norad_id)
    if debris_parsed is None:
        raise NotFoundError(
            f"デブリ NORAD {alert.debris_norad_id} の TLE が見つかりません。"
        )

    satellite = parse_tle(sat.tle)
    tca = _ensure_aware(alert.tca)
    start = tca - timedelta(hours=REFINE_WINDOW_HOURS)
    duration_days = (2.0 * REFINE_WINDOW_HOURS) / 24.0

    sat_pts = propagate_orbit(
        satellite, start, duration_days=duration_days, step_minutes=REFINE_STEP_MINUTES
    )
    deb_pts = propagate_orbit(
        debris_parsed, start, duration_days=duration_days, step_minutes=REFINE_STEP_MINUTES
    )
    ca = find_closest_approach(sat_pts, deb_pts)
    tca_index = _find_tca_index(sat_pts, deb_pts, alert.tca)

    events = [_synthetic_event(alert, debris_parsed.text, tca_index)]
    debris_propagated = [
        (alert.debris_norad_id, alert.debris_name, debris_parsed.text, deb_pts)
    ]

    refined_events, _records_fetched, _merged, _degraded = apply_spacetrack_cdm_to_events(
        events,
        satellite,
        DEFAULT_THRESHOLD_KM,
        sat_pts,
        debris_propagated,
    )
    event = refined_events[0]

    if event.sigma_source == "cdm_covariance":
        pc_refined = float(event.pc_foster if event.pc_foster is not None else event.pc)
        pc_method = "cdm_rtn"
        covariance_source = "spacetrack_cdm"
    else:
        enc = pc_for_tle_pair_at_index(
            satellite,
            debris_parsed,
            sat_pts,
            deb_pts,
            tca_index,
            use_anisotropic_cov=True,
        )
        pc_refined = float(enc.foster)
        pc_method = "tle_rtn"
        covariance_source = "tle_age"

    refinement = AlertPcRefinement(
        alert_id=alert.id,
        pc_screening=alert.pc,
        pc_refined=pc_refined,
        pc_method=pc_method,
        covariance_source=covariance_source,
        miss_distance_km=ca.miss_distance_km,
        api_key_id=api_key_id,
    )
    db.add(refinement)
    db.flush()

    from backend.app.services import audit_service

    audit_service.log_audit(
        db,
        fleet_id=alert.fleet_id,
        action="alert.pc_refine",
        resource_type="alert",
        resource_id=alert.id,
        api_key_id=api_key_id,
        detail={
            "refinement_id": str(refinement.id),
            "pc_screening": alert.pc,
            "pc_refined": pc_refined,
            "pc_method": pc_method,
            "covariance_source": covariance_source,
        },
    )
    db.commit()
    db.refresh(refinement)
    return refinement


def list_pc_refinements(db: Session, alert_id: uuid.UUID) -> list[AlertPcRefinement]:
    alert = db.get(ConjunctionAlert, alert_id)
    if alert is None:
        raise NotFoundError("アラートが見つかりません。")
    return list(
        db.execute(
            select(AlertPcRefinement)
            .where(AlertPcRefinement.alert_id == alert_id)
            .order_by(AlertPcRefinement.created_at.desc())
        )
        .scalars()
        .all()
    )
