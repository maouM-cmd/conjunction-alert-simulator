"""Shared breach state for Alertmanager push (Phase 10V)."""

from __future__ import annotations

import os

from backend.app.db.session import get_redis_url

REDIS_KEY_PREFIX = "cas:am:breach:"

_memory_state: dict[tuple[str, str], bool] = {}
_redis_client = None


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def breach_redis_state_enabled() -> bool:
    return _env_bool("ALERTMANAGER_PUSH_REDIS_STATE_ENABLED", default=False)


def _redis_key(fleet_id: str, alertname: str) -> str:
    return f"{REDIS_KEY_PREFIX}{fleet_id}:{alertname}"


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


def get_breach_state(fleet_id: str, alertname: str) -> bool:
    if _use_redis():
        client = _get_redis()
        assert client is not None
        raw = client.get(_redis_key(fleet_id, alertname))
        if raw is None:
            return False
        return raw == "1"
    return _memory_state.get((fleet_id, alertname), False)


def set_breach_state(fleet_id: str, alertname: str, is_breaching: bool) -> None:
    if _use_redis():
        client = _get_redis()
        assert client is not None
        client.set(_redis_key(fleet_id, alertname), "1" if is_breaching else "0")
        return
    _memory_state[(fleet_id, alertname)] = is_breaching


def reset_breach_state_for_tests() -> None:
    global _redis_client
    _memory_state.clear()
    client = _redis_client
    if client is not None and breach_redis_state_enabled():
        try:
            for key in client.scan_iter(match=f"{REDIS_KEY_PREFIX}*"):
                client.delete(key)
        except Exception:
            pass
    _redis_client = None


def reset_redis_client_for_tests() -> None:
    global _redis_client
    _redis_client = None
