"""Celery tasks for automatic Pc refinement (Phase 10E)."""

from __future__ import annotations

import uuid

from celery.utils.log import get_task_logger

from backend.app.db.session import get_session_factory
from backend.app.services import pc_refinement_service
from backend.app.tasks.celery_app import celery_app

logger = get_task_logger(__name__)


def _session():
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("DATABASE_URL が設定されていません。")
    return factory()


@celery_app.task(name="backend.app.tasks.pc_refinement_tasks.refine_alert_pc_task")
def refine_alert_pc_task(alert_id: str) -> dict:
    db = _session()
    try:
        refinement = pc_refinement_service.refine_alert_pc(
            db,
            uuid.UUID(alert_id),
            api_key_id=None,
            trigger_source=pc_refinement_service.TRIGGER_SCREENING_AUTO,
        )
        escalated = pc_refinement_service.maybe_escalate_after_refine(db, refinement)
        return {
            "alert_id": alert_id,
            "refinement_id": str(refinement.id),
            "pc_refined": refinement.pc_refined,
            "pc_method": refinement.pc_method,
            "trigger_source": refinement.trigger_source,
            "escalated": escalated,
        }
    except pc_refinement_service.PcRefinementServiceError as exc:
        logger.warning("Auto Pc refine failed for alert %s: %s", alert_id, exc)
        return {"alert_id": alert_id, "error": str(exc)}
    finally:
        db.close()
