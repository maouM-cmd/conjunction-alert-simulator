"""Execute a screening run using batch analysis."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from backend.app.db.models import ScreeningRun
from backend.app.services.screening_orchestrator import (
    ScreeningOrchestratorError,
    execute_screening_run as orchestrate_run,
)


class ScreeningRunnerError(Exception):
    pass


def execute_screening_run(db: Session, run_id: uuid.UUID) -> ScreeningRun:
    try:
        return orchestrate_run(db, run_id)
    except ScreeningOrchestratorError as exc:
        raise ScreeningRunnerError(str(exc)) from exc
