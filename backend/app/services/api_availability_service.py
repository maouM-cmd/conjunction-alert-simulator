"""Rolling-window API availability for SLO (Phase 10H / 10J)."""

from __future__ import annotations

import os
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass

_BUCKET_SECONDS = 3600
BUCKET_SECONDS = _BUCKET_SECONDS


@dataclass(frozen=True)
class ApiAvailabilitySummary:
    availability_ratio: float | None
    availability_percent: float | None
    slo_target_percent: float
    slo_ok: bool
    sample_window_hours: float
    request_count: int
    errors_5xx: int


_lock = threading.Lock()
_buckets: deque[tuple[int, int, int]] = deque()


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        return float(raw)
    except ValueError:
        return default


def api_slo_target_percent() -> float:
    return max(_env_float("SLA_API_TARGET_PERCENT", 99.9), 0.0)


def api_slo_target_ratio() -> float:
    return api_slo_target_percent() / 100.0


def api_rolling_window_hours() -> float:
    return max(_env_float("SLA_API_ROLLING_WINDOW_HOURS", 720.0), 1.0)


def _current_bucket_epoch() -> int:
    now = int(time.time())
    return now - (now % _BUCKET_SECONDS)


def _prune_buckets(window_seconds: float) -> None:
    cutoff = _current_bucket_epoch() - int(window_seconds)
    while _buckets and _buckets[0][0] < cutoff:
        _buckets.popleft()


def _get_or_create_bucket(epoch: int) -> tuple[int, int, int]:
    if _buckets and _buckets[-1][0] == epoch:
        return _buckets[-1]
    entry = (epoch, 0, 0)
    _buckets.append(entry)
    return entry


def replace_memory_buckets(entries: list[tuple[int, int, int]] | tuple) -> None:
    with _lock:
        _buckets.clear()
        for entry in entries:
            _buckets.append(entry)


def load_memory_buckets() -> list[tuple[int, int, int]]:
    with _lock:
        return list(_buckets)


def _record_memory(status_code: int) -> None:
    is_5xx = status_code >= 500
    epoch = _current_bucket_epoch()
    window_seconds = api_rolling_window_hours() * 3600.0

    with _lock:
        _prune_buckets(window_seconds)
        bucket = _get_or_create_bucket(epoch)
        total, errors = bucket[1], bucket[2]
        _buckets[-1] = (epoch, total + 1, errors + (1 if is_5xx else 0))


def record_http_status(status_code: int, fleet_id: uuid.UUID | None = None) -> None:
    from backend.app.db.session import get_session_factory, is_database_configured
    from backend.app.services import fleet_api_availability_service, slo_persistence_service

    if fleet_id is not None:
        fleet_api_availability_service.record_fleet_http_status(fleet_id, status_code)

    if slo_persistence_service.slo_api_persist_enabled() and is_database_configured():
        factory = get_session_factory()
        if factory is not None:
            db = factory()
            try:
                epoch = _current_bucket_epoch()
                is_5xx = status_code >= 500
                slo_persistence_service.upsert_hourly_bucket(
                    db,
                    epoch,
                    inc_total=1,
                    inc_5xx=1 if is_5xx else 0,
                )
                return
            except Exception:
                pass
            finally:
                db.close()

    _record_memory(status_code)


def reset_availability_for_tests() -> None:
    with _lock:
        _buckets.clear()
    from backend.app.services import fleet_api_availability_service, slo_persistence_service

    fleet_api_availability_service.reset_fleet_availability_for_tests()

    slo_persistence_service.reset_hydration_for_tests()
    from backend.app.db.session import get_session_factory

    factory = get_session_factory()
    if factory is not None:
        db = factory()
        try:
            slo_persistence_service.clear_buckets_for_tests(db)
        finally:
            db.close()


def summary_from_totals(total: int, errors_5xx: int) -> ApiAvailabilitySummary:
    target_percent = api_slo_target_percent()
    target_ratio = target_percent / 100.0
    window_hours = api_rolling_window_hours()

    if total == 0:
        return ApiAvailabilitySummary(
            availability_ratio=None,
            availability_percent=None,
            slo_target_percent=target_percent,
            slo_ok=True,
            sample_window_hours=window_hours,
            request_count=0,
            errors_5xx=0,
        )

    ratio = (total - errors_5xx) / total
    percent = ratio * 100.0
    slo_ok = ratio >= target_ratio

    return ApiAvailabilitySummary(
        availability_ratio=ratio,
        availability_percent=percent,
        slo_target_percent=target_percent,
        slo_ok=slo_ok,
        sample_window_hours=window_hours,
        request_count=total,
        errors_5xx=errors_5xx,
    )


def _compute_from_memory() -> ApiAvailabilitySummary:
    window_hours = api_rolling_window_hours()
    window_seconds = window_hours * 3600.0

    with _lock:
        _prune_buckets(window_seconds)
        total = sum(b[1] for b in _buckets)
        errors_5xx = sum(b[2] for b in _buckets)

    return summary_from_totals(total, errors_5xx)


def compute_api_availability() -> ApiAvailabilitySummary:
    from backend.app.db.session import get_session_factory, is_database_configured
    from backend.app.services import slo_persistence_service

    if slo_persistence_service.slo_api_persist_enabled() and is_database_configured():
        factory = get_session_factory()
        if factory is not None:
            db = factory()
            try:
                return slo_persistence_service.compute_availability_from_db(db)
            except Exception:
                pass
            finally:
                db.close()

    return _compute_from_memory()
