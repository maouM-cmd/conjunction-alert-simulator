"""Prometheus metrics endpoint (Phase 9D / 10B)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import func, select

from backend.app.db.models import ConjunctionAlert, ScreeningRun
from backend.app.db.session import get_redis_url, get_session_factory, is_database_configured
from backend.app.metrics_registry import (
    cas_api_availability_ratio,
    cas_api_slo_ok,
    cas_celery_queue_depth,
    cas_fleet_alerts_total,
    cas_fleet_api_availability_ratio,
    cas_fleet_api_slo_ok,
    cas_fleet_open_alerts_breach,
    cas_info,
    cas_open_alerts,
    cas_screening_lag_seconds,
    cas_screening_overdue_fleets,
    cas_screening_runs,
    registry,
)
from backend.app.services import (
    api_availability_service,
    fleet_alert_metrics_service,
    fleet_api_availability_service,
    sla_service,
    slo_persistence_service,
)
from backend.app.version import APP_VERSION

router = APIRouter(tags=["metrics"])


def _collect_db_metrics() -> None:
    factory = get_session_factory()
    if factory is None:
        return
    db = factory()
    try:
        if slo_persistence_service.slo_api_persist_enabled():
            slo_persistence_service.ensure_hydrated_and_pruned(db)

        open_count = int(
            db.execute(
                select(func.count())
                .select_from(ConjunctionAlert)
                .where(ConjunctionAlert.status == "open")
            ).scalar_one()
        )
        cas_open_alerts.set(open_count)

        rows = db.execute(
            select(ScreeningRun.status, func.count()).group_by(ScreeningRun.status)
        ).all()
        for status, count in rows:
            cas_screening_runs.labels(status=status).set(int(count))

        lags, overdue = sla_service.collect_screening_lag_metrics(db)
        cas_screening_lag_seconds.clear()
        for fleet_id, lag in lags.items():
            cas_screening_lag_seconds.labels(fleet_id=fleet_id).set(lag)
        cas_screening_overdue_fleets.set(overdue)

        if fleet_alert_metrics_service.fleet_alert_metrics_enabled():
            counts = fleet_alert_metrics_service.collect_fleet_alert_counts(db)
            threshold = fleet_alert_metrics_service.fleet_open_alert_threshold()
            cas_fleet_alerts_total.clear()
            cas_fleet_open_alerts_breach.clear()
            for fleet_id, status_counts in counts.items():
                fleet_id_str = str(fleet_id)
                open_count = status_counts.get("open", 0)
                for status, count in status_counts.items():
                    cas_fleet_alerts_total.labels(fleet_id=fleet_id_str, status=status).set(count)
                breach = 1.0 if open_count > threshold else 0.0
                cas_fleet_open_alerts_breach.labels(fleet_id=fleet_id_str).set(breach)
    finally:
        db.close()


def _collect_queue_depth() -> None:
    url = get_redis_url()
    if not url:
        return
    try:
        import redis

        client = redis.from_url(url, decode_responses=True)
        depth = int(client.llen("celery"))
        cas_celery_queue_depth.set(depth)
    except Exception:
        pass


def _collect_api_slo_metrics() -> None:
    summary = api_availability_service.compute_api_availability()
    if summary.availability_ratio is None:
        cas_api_availability_ratio.set(1.0)
        cas_api_slo_ok.set(1.0)
    else:
        cas_api_availability_ratio.set(summary.availability_ratio)
        cas_api_slo_ok.set(1.0 if summary.slo_ok else 0.0)

    if not fleet_api_availability_service.fleet_api_slo_enabled():
        return

    fleet_ids: set[str] = set()
    for fleet_id in fleet_api_availability_service.list_fleet_ids_with_memory_samples():
        fleet_ids.add(str(fleet_id))

    factory = get_session_factory()
    if factory is not None and slo_persistence_service.slo_api_persist_enabled():
        db = factory()
        try:
            window_seconds = int(api_availability_service.api_rolling_window_hours() * 3600.0)
            now_epoch = int(__import__("time").time())
            since_epoch = now_epoch - (now_epoch % 3600) - window_seconds
            for fleet_id in slo_persistence_service.list_distinct_fleet_ids(db, since_epoch):
                fleet_ids.add(str(fleet_id))
        finally:
            db.close()

    cas_fleet_api_availability_ratio.clear()
    cas_fleet_api_slo_ok.clear()
    for fleet_id_str in fleet_ids:
        fleet_summary = fleet_api_availability_service.compute_fleet_api_availability(
            uuid.UUID(fleet_id_str)
        )
        if fleet_summary is None:
            continue
        if fleet_summary.availability_ratio is None:
            cas_fleet_api_availability_ratio.labels(fleet_id=fleet_id_str).set(1.0)
            cas_fleet_api_slo_ok.labels(fleet_id=fleet_id_str).set(1.0)
        else:
            cas_fleet_api_availability_ratio.labels(fleet_id=fleet_id_str).set(
                fleet_summary.availability_ratio
            )
            cas_fleet_api_slo_ok.labels(fleet_id=fleet_id_str).set(
                1.0 if fleet_summary.slo_ok else 0.0
            )


@router.get("/metrics")
def metrics() -> Response:
    cas_info.info({"version": APP_VERSION})
    _collect_api_slo_metrics()
    if is_database_configured():
        _collect_db_metrics()
    _collect_queue_depth()
    payload = generate_latest(registry)
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
