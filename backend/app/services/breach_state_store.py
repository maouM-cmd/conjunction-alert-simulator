"""Shared breach state for Alertmanager push (Phase 10V / 10X)."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.session import get_redis_url, get_session_factory, is_database_configured

REDIS_KEY_PREFIX = "cas:am:breach:"
REDIS_STICKY_KEY_PREFIX = "cas:am:breach:sticky:"
FLEET_ALERTNAMES = (
    "CASFleetOpenAlertsHigh",
    "CASFleetHighRiskOpenAlerts",
)

_memory_state: dict[tuple[str, str], bool] = {}
_memory_sticky: dict[tuple[str, str], bool] = {}
_redis_client = None


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def breach_redis_state_enabled() -> bool:
    return _env_bool("ALERTMANAGER_PUSH_REDIS_STATE_ENABLED", default=False)


def breach_db_state_enabled() -> bool:
    return _env_bool("ALERTMANAGER_PUSH_DB_STATE_ENABLED", default=False)


def shared_breach_state_enabled() -> bool:
    return breach_redis_state_enabled() or breach_db_state_enabled()


def breach_manual_override_enabled() -> bool:
    return _env_bool("ALERTMANAGER_BREACH_STATE_MANUAL_OVERRIDE_ENABLED", default=False)


def breach_sticky_override_enabled() -> bool:
    return _env_bool("ALERTMANAGER_BREACH_STATE_STICKY_OVERRIDE_ENABLED", default=False)


@dataclass(frozen=True)
class FleetBreachStateItem:
    alertname: str
    is_breaching: bool
    is_sticky: bool = False


@dataclass(frozen=True)
class FleetBreachStateRow:
    fleet_id: str
    fleet_name: str | None
    alertname: str
    is_breaching: bool
    is_sticky: bool = False


def breach_state_backend() -> str:
    if _use_redis():
        return "redis"
    if _use_db():
        return "db"
    return "memory"


def list_fleet_breach_states(fleet_id: str) -> list[FleetBreachStateItem]:
    return [
        FleetBreachStateItem(
            alertname=alertname,
            is_breaching=get_breach_state(fleet_id, alertname),
            is_sticky=is_sticky_override(fleet_id, alertname),
        )
        for alertname in FLEET_ALERTNAMES
    ]


def list_all_fleet_breach_states(db: Session) -> list[FleetBreachStateRow]:
    from backend.app.db.models import Fleet

    fleets = db.execute(
        select(Fleet).where(Fleet.active.is_(True)).order_by(Fleet.name)
    ).scalars().all()
    rows: list[FleetBreachStateRow] = []
    for fleet in fleets:
        fleet_id = str(fleet.id)
        for alertname in FLEET_ALERTNAMES:
            rows.append(
                FleetBreachStateRow(
                    fleet_id=fleet_id,
                    fleet_name=fleet.name,
                    alertname=alertname,
                    is_breaching=get_breach_state(fleet_id, alertname),
                    is_sticky=is_sticky_override(fleet_id, alertname),
                )
            )
    return rows


def is_valid_fleet_alertname(alertname: str) -> bool:
    return alertname in FLEET_ALERTNAMES


def _redis_key(fleet_id: str, alertname: str) -> str:
    return f"{REDIS_KEY_PREFIX}{fleet_id}:{alertname}"


def _redis_sticky_key(fleet_id: str, alertname: str) -> str:
    return f"{REDIS_STICKY_KEY_PREFIX}{fleet_id}:{alertname}"


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if not breach_redis_state_enabled():
        return None
    url = get_redis_url()
    if not url:
        return None
    try:
        import redis

        _redis_client = redis.from_url(url, decode_responses=True)
        _redis_client.ping()
        return _redis_client
    except Exception:
        return None


def _use_redis() -> bool:
    return breach_redis_state_enabled() and _get_redis() is not None


def _use_db() -> bool:
    return breach_db_state_enabled() and is_database_configured() and get_session_factory() is not None


def _parse_fleet_id(fleet_id: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(fleet_id)
    except ValueError:
        return None


def _get_db_state(fleet_id: str, alertname: str) -> bool:
    factory = get_session_factory()
    if factory is None:
        return False
    fid = _parse_fleet_id(fleet_id)
    if fid is None:
        return False
    from backend.app.db.models import FleetAlertBreachState

    db = factory()
    try:
        row = db.get(FleetAlertBreachState, (fid, alertname))
        if row is None:
            return False
        return row.is_breaching
    finally:
        db.close()


def _get_db_sticky(fleet_id: str, alertname: str) -> bool:
    factory = get_session_factory()
    if factory is None:
        return False
    fid = _parse_fleet_id(fleet_id)
    if fid is None:
        return False
    from backend.app.db.models import FleetAlertBreachState

    db = factory()
    try:
        row = db.get(FleetAlertBreachState, (fid, alertname))
        if row is None:
            return False
        return row.is_manual_sticky
    finally:
        db.close()


def _set_db_state(fleet_id: str, alertname: str, is_breaching: bool) -> None:
    factory = get_session_factory()
    if factory is None:
        return
    fid = _parse_fleet_id(fleet_id)
    if fid is None:
        return
    from backend.app.db.models import FleetAlertBreachState

    db = factory()
    try:
        row = db.get(FleetAlertBreachState, (fid, alertname))
        if row is None:
            row = FleetAlertBreachState(
                fleet_id=fid,
                alertname=alertname,
                is_breaching=is_breaching,
                is_manual_sticky=False,
            )
            db.add(row)
        else:
            row.is_breaching = is_breaching
            row.updated_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def _set_db_sticky(fleet_id: str, alertname: str, is_sticky: bool) -> None:
    factory = get_session_factory()
    if factory is None:
        return
    fid = _parse_fleet_id(fleet_id)
    if fid is None:
        return
    from backend.app.db.models import FleetAlertBreachState

    db = factory()
    try:
        row = db.get(FleetAlertBreachState, (fid, alertname))
        if row is None:
            if not is_sticky:
                return
            row = FleetAlertBreachState(
                fleet_id=fid,
                alertname=alertname,
                is_breaching=False,
                is_manual_sticky=True,
            )
            db.add(row)
        else:
            row.is_manual_sticky = is_sticky
            row.updated_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def _clear_db_state() -> None:
    factory = get_session_factory()
    if factory is None:
        return
    from backend.app.db.models import FleetAlertBreachState

    db = factory()
    try:
        for row in db.query(FleetAlertBreachState).all():
            db.delete(row)
        db.commit()
    finally:
        db.close()


def get_breach_state(fleet_id: str, alertname: str) -> bool:
    if _use_redis():
        client = _get_redis()
        assert client is not None
        raw = client.get(_redis_key(fleet_id, alertname))
        if raw is None:
            return False
        return raw == "1"
    if _use_db():
        return _get_db_state(fleet_id, alertname)
    return _memory_state.get((fleet_id, alertname), False)


def set_breach_state(fleet_id: str, alertname: str, is_breaching: bool) -> None:
    if _use_redis():
        client = _get_redis()
        assert client is not None
        client.set(_redis_key(fleet_id, alertname), "1" if is_breaching else "0")
        return
    if _use_db():
        _set_db_state(fleet_id, alertname, is_breaching)
        return
    _memory_state[(fleet_id, alertname)] = is_breaching


def is_sticky_override(fleet_id: str, alertname: str) -> bool:
    if not breach_sticky_override_enabled():
        return False
    if _use_redis():
        client = _get_redis()
        assert client is not None
        return client.get(_redis_sticky_key(fleet_id, alertname)) == "1"
    if _use_db():
        return _get_db_sticky(fleet_id, alertname)
    return _memory_sticky.get((fleet_id, alertname), False)


def set_sticky_override(fleet_id: str, alertname: str, is_sticky: bool) -> None:
    if not breach_sticky_override_enabled():
        return
    if _use_redis():
        client = _get_redis()
        assert client is not None
        key = _redis_sticky_key(fleet_id, alertname)
        if is_sticky:
            client.set(key, "1")
        else:
            client.delete(key)
        return
    if _use_db():
        _set_db_sticky(fleet_id, alertname, is_sticky)
        return
    if is_sticky:
        _memory_sticky[(fleet_id, alertname)] = True
    else:
        _memory_sticky.pop((fleet_id, alertname), None)


def clear_sticky_override(fleet_id: str, alertname: str) -> None:
    set_sticky_override(fleet_id, alertname, False)


def reset_breach_state_for_tests() -> None:
    global _redis_client
    _memory_state.clear()
    _memory_sticky.clear()
    client = _redis_client
    if client is not None and breach_redis_state_enabled():
        try:
            for key in client.scan_iter(match=f"{REDIS_KEY_PREFIX}*"):
                client.delete(key)
            for key in client.scan_iter(match=f"{REDIS_STICKY_KEY_PREFIX}*"):
                client.delete(key)
        except Exception:
            pass
    _redis_client = None
    if breach_db_state_enabled():
        _clear_db_state()


def reset_redis_client_for_tests() -> None:
    global _redis_client
    _redis_client = None
