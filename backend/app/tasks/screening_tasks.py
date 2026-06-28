"""Celery tasks for scheduled screening."""

from __future__ import annotations

import uuid

from celery.exceptions import MaxRetriesExceededError
from celery.utils.log import get_task_logger

from backend.app.db.session import get_session_factory
from backend.app.services import screening_runner, screening_service
from backend.app.tasks.celery_app import celery_app

logger = get_task_logger(__name__)
MAX_RETRIES = 3


def mark_dead_letter_on_final_failure(self, exc, task_id, args, kwargs, einfo):
    if isinstance(exc, MaxRetriesExceededError) and args:
        db = _session()
        try:
            run = screening_service.get_run(db, uuid.UUID(args[0]))
            screening_service.mark_run_failed(
                db,
                run,
                error_message=str(exc),
                dead_letter=True,
                retry_count=MAX_RETRIES,
            )
        finally:
            db.close()


def _session():
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("DATABASE_URL が設定されていません。")
    return factory()


@celery_app.task(
    bind=True,
    name="backend.app.tasks.screening_tasks.run_screening_job",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=MAX_RETRIES,
)
def run_screening_job(self, run_id: str) -> dict:
    db = _session()
    try:
        run_uuid = uuid.UUID(run_id)
        run = screening_service.get_run(db, run_uuid)
        run.retry_count = self.request.retries
        db.commit()
        screening_runner.execute_screening_run(db, run_uuid)
        run = screening_service.get_run(db, run_uuid)
        return {
            "run_id": run_id,
            "status": run.status,
            "event_count": run.event_count,
            "degraded": run.degraded,
        }
    except screening_runner.ScreeningRunnerError:
        raise
    except Exception as exc:
        logger.exception("Screening job failed: %s", run_id)
        raise exc
    finally:
        db.close()


@celery_app.task(name="backend.app.tasks.screening_tasks.poll_due_schedules")
def poll_due_schedules() -> dict:
    db = _session()
    enqueued = 0
    try:
        due = screening_service.list_due_schedules(db)
        for schedule in due:
            run = screening_service.create_run(
                db,
                fleet_id=schedule.fleet_id,
                schedule_id=schedule.id,
            )
            run_screening_job.delay(str(run.id))
            enqueued += 1
        return {"enqueued": enqueued}
    finally:
        db.close()


run_screening_job.on_failure = mark_dead_letter_on_final_failure
