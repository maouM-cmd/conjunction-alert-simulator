"""Shared Prometheus registry and metric handles (Phase 10B)."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Info

registry = CollectorRegistry()

cas_info = Info("cas_info", "CAS application info", registry=registry)
cas_open_alerts = Gauge(
    "cas_open_alerts_total",
    "Count of open conjunction alerts",
    registry=registry,
)
cas_screening_runs = Gauge(
    "cas_screening_runs_total",
    "Screening runs by status",
    ["status"],
    registry=registry,
)
cas_celery_queue_depth = Gauge(
    "cas_celery_queue_depth",
    "Celery default queue depth (Redis LLEN)",
    registry=registry,
)
cas_screening_lag_seconds = Gauge(
    "cas_screening_lag_seconds",
    "Seconds since last completed parent screening run",
    ["fleet_id"],
    registry=registry,
)
cas_screening_overdue_fleets = Gauge(
    "cas_screening_overdue_fleets",
    "Fleets exceeding screening SLA lag threshold",
    registry=registry,
)
cas_http_requests_total = Counter(
    "cas_http_requests_total",
    "HTTP requests by method and status class",
    ["method", "status_class"],
    registry=registry,
)
cas_api_availability_ratio = Gauge(
    "cas_api_availability_ratio",
    "Rolling-window API availability ratio (1 - 5xx/total)",
    registry=registry,
)
cas_api_slo_ok = Gauge(
    "cas_api_slo_ok",
    "1 if API availability meets SLA target, else 0",
    registry=registry,
)
cas_fleet_api_availability_ratio = Gauge(
    "cas_fleet_api_availability_ratio",
    "Per-fleet rolling-window API availability ratio (Phase 10N)",
    ["fleet_id"],
    registry=registry,
)
cas_fleet_api_slo_ok = Gauge(
    "cas_fleet_api_slo_ok",
    "1 if fleet API availability meets SLA target, else 0 (Phase 10N)",
    ["fleet_id"],
    registry=registry,
)
cas_fleet_alerts_total = Gauge(
    "cas_fleet_alerts_total",
    "Per-fleet conjunction alert counts by status (Phase 10Q)",
    ["fleet_id", "status"],
    registry=registry,
)
cas_fleet_open_alerts_breach = Gauge(
    "cas_fleet_open_alerts_breach",
    "1 if fleet open alert count exceeds threshold, else 0 (Phase 10Q)",
    ["fleet_id"],
    registry=registry,
)


def status_class(status_code: int) -> str:
    if status_code < 400:
        return "2xx"
    if status_code < 500:
        return "4xx"
    return "5xx"


def record_http_request(method: str, status_code: int) -> None:
    cas_http_requests_total.labels(method=method, status_class=status_class(status_code)).inc()
