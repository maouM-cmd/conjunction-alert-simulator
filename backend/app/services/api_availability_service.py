"""Rolling-window API availability for SLO (Phase 10H)."""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from dataclasses import dataclass

_BUCKET_SECONDS = 3600


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


def record_http_status(status_code: int) -> None:
    is_5xx = status_code >= 500
    epoch = _current_bucket_epoch()
    window_seconds = api_rolling_window_hours() * 3600.0

    with _lock:
        _prune_buckets(window_seconds)
        bucket = _get_or_create_bucket(epoch)
        total, errors = bucket[1], bucket[2]
        _buckets[-1] = (epoch, total + 1, errors + (1 if is_5xx else 0))


def reset_availability_for_tests() -> None:
    with _lock:
        _buckets.clear()


def compute_api_availability() -> ApiAvailabilitySummary:
    target_percent = api_slo_target_percent()
    target_ratio = target_percent / 100.0
    window_hours = api_rolling_window_hours()
    window_seconds = window_hours * 3600.0

    with _lock:
        _prune_buckets(window_seconds)
        total = sum(b[1] for b in _buckets)
        errors_5xx = sum(b[2] for b in _buckets)

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
