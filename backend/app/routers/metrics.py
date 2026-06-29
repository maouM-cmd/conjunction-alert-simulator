"""Prometheus metrics endpoint (Phase 9D)."""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Gauge, Info, generate_latest
from sqlalchemy import func, select

from backend.app.db.models import ConjunctionAlert, ScreeningRun
from backend.app.db.session import get_redis_url, get_session_factory, is_database_configured
from backend.app.version import APP_VERSION

router = APIRouter(tags=["metrics"])

_registry = CollectorRegistry()
_cas_info = Info("cas_info", "CAS application info", registry=_registry)
_cas_open_alerts = Gauge(
    "cas_open_alerts_total",
    "Count of open conjunction alerts",
    registry=_registry,
)
_cas_screening_runs = Gauge(
    "cas_screening_runs_total",
    "Screening runs by status",
    ["status"],
    registry=_registry,
)
_cas_celery_queue_depth = Gauge(
    "cas_celery_queue_depth",
    "Celery default queue depth (Redis LLEN)",
    registry=_registry,
)


def _collect_db_metrics() -> None:
    factory = get_session_factory()
    if factory is None:
        return
    db = factory()
    try:
        open_count = int(
            db.execute(
                select(func.count())
                .select_from(ConjunctionAlert)
                .where(ConjunctionAlert.status == "open")
            ).scalar_one()
        )
        _cas_open_alerts.set(open_count)

        rows = db.execute(
            select(ScreeningRun.status, func.count())
            .group_by(ScreeningRun.status)
        ).all()
        for status, count in rows:
            _cas_screening_runs.labels(status=status).set(int(count))
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
        _cas_celery_queue_depth.set(depth)
    except Exception:
        pass


@router.get("/metrics")
def metrics() -> Response:
    _cas_info.info({"version": APP_VERSION})
    if is_database_configured():
        _collect_db_metrics()
    _collect_queue_depth()
    payload = generate_latest(_registry)
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
