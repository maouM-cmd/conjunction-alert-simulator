"""Per-fleet rolling-window API availability (Phase 10N)."""

from __future__ import annotations

import os
import threading
import time
import uuid
from collections import deque

from backend.app.services.api_availability_service import (
    ApiAvailabilitySummary,
    BUCKET_SECONDS,
    api_rolling_window_hours,
    summary_from_totals,
)

_lock = threading.Lock()
_fleet_buckets: dict[uuid.UUID, deque[tuple[int, int, int]]] = {}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def fleet_api_slo_enabled() -> bool:
    return _env_bool("SLA_FLEET_API_SLO_ENABLED", default=False)


def _current_bucket_epoch() -> int:
    now = int(time.time())
    return now - (now % BUCKET_SECONDS)


def _prune_fleet_buckets(fleet_id: uuid.UUID, window_seconds: float) -> None:
    cutoff = _current_bucket_epoch() - int(window_seconds)
    buckets = _fleet_buckets.get(fleet_id)
    if buckets is None:
        return
    while buckets and buckets[0][0] < cutoff:
        buckets.popleft()
    if not buckets:
        _fleet_buckets.pop(fleet_id, None)


def _get_or_create_fleet_bucket(
    fleet_id: uuid.UUID,
    epoch: int,
) -> tuple[int, int, int]:
    buckets = _fleet_buckets.setdefault(fleet_id, deque())
    if buckets and buckets[-1][0] == epoch:
        return buckets[-1]
    entry = (epoch, 0, 0)
    buckets.append(entry)
    return entry


def replace_fleet_memory_buckets(
    fleet_id: uuid.UUID,
    entries: list[tuple[int, int, int]],
) -> None:
    with _lock:
        if entries:
            _fleet_buckets[fleet_id] = deque(entries)
        else:
            _fleet_buckets.pop(fleet_id, None)


def load_fleet_memory_buckets(fleet_id: uuid.UUID) -> list[tuple[int, int, int]]:
    with _lock:
        buckets = _fleet_buckets.get(fleet_id)
        return list(buckets) if buckets else []


def list_fleet_ids_with_memory_samples() -> list[uuid.UUID]:
    with _lock:
        return list(_fleet_buckets.keys())


def _record_fleet_memory(fleet_id: uuid.UUID, status_code: int) -> None:
    is_5xx = status_code >= 500
    epoch = _current_bucket_epoch()
    window_seconds = api_rolling_window_hours() * 3600.0

    with _lock:
        _prune_fleet_buckets(fleet_id, window_seconds)
        bucket = _get_or_create_fleet_bucket(fleet_id, epoch)
        total, errors = bucket[1], bucket[2]
        buckets = _fleet_buckets[fleet_id]
        buckets[-1] = (epoch, total + 1, errors + (1 if is_5xx else 0))


def record_fleet_http_status(fleet_id: uuid.UUID, status_code: int) -> None:
    if not fleet_api_slo_enabled():
        return

    from backend.app.db.session import get_session_factory, is_database_configured
    from backend.app.services import slo_persistence_service

    if slo_persistence_service.slo_api_persist_enabled() and is_database_configured():
        factory = get_session_factory()
        if factory is not None:
            db = factory()
            try:
                epoch = _current_bucket_epoch()
                is_5xx = status_code >= 500
                slo_persistence_service.upsert_fleet_hourly_bucket(
                    db,
                    fleet_id,
                    epoch,
                    inc_total=1,
                    inc_5xx=1 if is_5xx else 0,
                )
                return
            except Exception:
                pass
            finally:
                db.close()

    _record_fleet_memory(fleet_id, status_code)


def _compute_from_memory(fleet_id: uuid.UUID) -> ApiAvailabilitySummary:
    window_hours = api_rolling_window_hours()
    window_seconds = window_hours * 3600.0

    with _lock:
        _prune_fleet_buckets(fleet_id, window_seconds)
        buckets = _fleet_buckets.get(fleet_id, deque())
        total = sum(b[1] for b in buckets)
        errors_5xx = sum(b[2] for b in buckets)

    return summary_from_totals(total, errors_5xx)


def compute_fleet_api_availability(fleet_id: uuid.UUID) -> ApiAvailabilitySummary | None:
    if not fleet_api_slo_enabled():
        return None

    from backend.app.db.session import get_session_factory, is_database_configured
    from backend.app.services import slo_persistence_service

    if slo_persistence_service.slo_api_persist_enabled() and is_database_configured():
        factory = get_session_factory()
        if factory is not None:
            db = factory()
            try:
                return slo_persistence_service.compute_fleet_availability_from_db(db, fleet_id)
            except Exception:
                pass
            finally:
                db.close()

    return _compute_from_memory(fleet_id)


def reset_fleet_availability_for_tests() -> None:
    with _lock:
        _fleet_buckets.clear()
