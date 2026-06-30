"""Celery application configuration."""

from __future__ import annotations

import os

from celery import Celery

from backend.app.db.session import get_redis_url
from backend.app.services.alertmanager_push_service import push_celery_interval_sec
from backend.app.services.fleet_alert_rules_apply_service import (
    prometheus_reload_history_purge_interval_seconds,
)

redis_url = get_redis_url() or "redis://localhost:6379/0"

celery_app = Celery(
    "cas",
    broker=redis_url,
    backend=redis_url,
    include=[
        "backend.app.tasks.screening_tasks",
        "backend.app.tasks.pc_refinement_tasks",
        "backend.app.tasks.mitigation_tasks",
        "backend.app.tasks.alertmanager_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "poll-due-screening-schedules": {
            "task": "backend.app.tasks.screening_tasks.poll_due_schedules",
            "schedule": 60.0,
        },
        "purge-old-audit-logs": {
            "task": "backend.app.tasks.screening_tasks.purge_old_audit_logs",
            "schedule": 86400.0,
        },
        "sync-fleet-alert-breaches": {
            "task": "backend.app.tasks.alertmanager_tasks.sync_fleet_alert_breaches",
            "schedule": push_celery_interval_sec(),
        },
        "purge-old-breach-history": {
            "task": "backend.app.tasks.alertmanager_tasks.purge_old_breach_history",
            "schedule": 86400.0,
        },
        "purge-stale-prometheus-reload-history": {
            "task": "backend.app.tasks.alertmanager_tasks.purge_stale_prometheus_reload_history",
            "schedule": prometheus_reload_history_purge_interval_seconds(),
        },
    },
)


def configure_celery_eager() -> None:
    """Use in-memory broker/backend for pytest (no Redis required)."""
    if os.getenv("CELERY_TASK_ALWAYS_EAGER", "").lower() in ("1", "true", "yes"):
        celery_app.conf.update(
            task_always_eager=True,
            task_store_eager_result=True,
            broker_url="memory://",
            result_backend="cache+memory://",
        )


configure_celery_eager()
