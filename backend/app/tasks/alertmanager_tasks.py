"""Celery tasks for Alertmanager fleet breach sync (Phase 10U)."""

from __future__ import annotations

from celery.utils.log import get_task_logger

from backend.app.db.session import get_session_factory
from backend.app.services import alertmanager_push_service, fleet_metrics_sync_service
from backend.app.tasks.celery_app import celery_app

logger = get_task_logger(__name__)


def _session():
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("DATABASE_URL が設定されていません。")
    return factory()


@celery_app.task(name="backend.app.tasks.alertmanager_tasks.sync_fleet_alert_breaches")
def sync_fleet_alert_breaches() -> dict[str, str]:
    if not alertmanager_push_service.alertmanager_push_celery_configured():
        return {"status": "skipped", "reason": "celery push not configured"}

    db = _session()
    try:
        fleet_metrics_sync_service.collect_and_export_fleet_metrics(db, sync_breaches=True)
    except Exception as exc:
        logger.exception("Fleet alert breach sync failed: %s", exc)
        return {"status": "error", "reason": str(exc)}
    finally:
        db.close()

    return {"status": "ok"}


@celery_app.task(name="backend.app.tasks.alertmanager_tasks.purge_old_breach_history")
def purge_old_breach_history() -> dict:
    from backend.app.services import breach_history_service

    if not breach_history_service.breach_history_enabled():
        return {"status": "skipped", "reason": "breach history not enabled"}

    db = _session()
    try:
        deleted = breach_history_service.purge_old_breach_history(db)
        return {"status": "ok", "deleted": deleted}
    finally:
        db.close()
