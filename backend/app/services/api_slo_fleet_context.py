"""Resolve fleet id for API SLO from request scope (Phase 10N)."""

from __future__ import annotations

import uuid

from backend.app.auth.principal import is_admin_key
from backend.app.db.session import get_session_factory, is_database_configured
from backend.app.services import api_key_service
from backend.app.services.auth_config import is_api_key_required
from backend.app.services.fleet_api_availability_service import fleet_api_slo_enabled


def fleet_id_from_scope(scope) -> uuid.UUID | None:
    state = scope.get("state")
    if state is not None:
        fleet_id = getattr(state, "fleet_id_for_api_slo", None)
        if fleet_id is not None:
            return fleet_id

    if not fleet_api_slo_enabled() or not is_api_key_required():
        return None

    headers = {name.decode("latin-1").lower(): value.decode("latin-1") for name, value in scope.get("headers", [])}
    api_key = headers.get("x-api-key")
    if not api_key or is_admin_key(api_key):
        return None

    if not is_database_configured():
        return None
    factory = get_session_factory()
    if factory is None:
        return None

    db = factory()
    try:
        record = api_key_service.verify_api_key(db, api_key)
        if record is None:
            return None
        return record.fleet_id
    finally:
        db.close()
