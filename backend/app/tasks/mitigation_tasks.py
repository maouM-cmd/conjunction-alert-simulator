"""Celery tasks for automatic mitigation sweep (Phase 10F)."""

from __future__ import annotations

import uuid

from celery.utils.log import get_task_logger

from backend.app.db.session import get_session_factory
from backend.app.services import mitigation_service
from backend.app.tasks.celery_app import celery_app

logger = get_task_logger(__name__)


def _session():
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("DATABASE_URL が設定されていません。")
    return factory()


@celery_app.task(name="backend.app.tasks.mitigation_tasks.mitigation_sweep_task")
def mitigation_sweep_task(alert_id: str) -> dict:
    db = _session()
    try:
        _previews, best = mitigation_service.run_alert_mitigation_sweep(
            db,
            uuid.UUID(alert_id),
            api_key_id=None,
            trigger_source=mitigation_service.TRIGGER_SCREENING_AUTO,
        )
        notified = mitigation_service.maybe_notify_mitigation_best(
            db, uuid.UUID(alert_id), best
        )
        planned = mitigation_service.maybe_auto_mitigation_plan(
            db, uuid.UUID(alert_id), best
        )
        return {
            "alert_id": alert_id,
            "trial_count": len(_previews),
            "best_preview_id": str(best.id) if best else None,
            "trigger_source": mitigation_service.TRIGGER_SCREENING_AUTO,
            "notified": notified,
            "auto_planned": planned is not None,
            "new_status": planned.status if planned else None,
        }
    except mitigation_service.MitigationServiceError as exc:
        logger.warning("Auto mitigation sweep failed for alert %s: %s", alert_id, exc)
        return {"alert_id": alert_id, "error": str(exc)}
    finally:
        db.close()
