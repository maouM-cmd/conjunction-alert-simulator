"""Celery application configuration."""

from __future__ import annotations

import os

from celery import Celery

from backend.app.db.session import get_redis_url

redis_url = get_redis_url() or "redis://localhost:6379/0"

celery_app = Celery(
    "cas",
    broker=redis_url,
    backend=redis_url,
    include=["backend.app.tasks.screening_tasks", "backend.app.tasks.pc_refinement_tasks"],
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
