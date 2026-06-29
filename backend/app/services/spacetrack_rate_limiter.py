"""Cross-process Space-Track request rate limiting via Redis (Phase 9D)."""

from __future__ import annotations

import time

from backend.app.db.session import get_redis_url

REDIS_KEY = "cas:spacetrack:last_request"
MIN_REQUEST_INTERVAL_SEC = 1.0

_last_request_at = 0.0
_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
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


def _local_throttle() -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < MIN_REQUEST_INTERVAL_SEC:
        time.sleep(MIN_REQUEST_INTERVAL_SEC - elapsed)
    _last_request_at = time.monotonic()


def acquire_spacetrack_slot() -> None:
    """Block until a Space-Track request slot is available (1 req/sec globally)."""
    client = _get_redis()
    if client is None:
        _local_throttle()
        return

    while True:
        now = time.time()
        raw = client.get(REDIS_KEY)
        if raw is not None:
            try:
                last = float(raw)
            except ValueError:
                last = 0.0
            wait = MIN_REQUEST_INTERVAL_SEC - (now - last)
            if wait > 0:
                time.sleep(wait)
                continue
        if client.set(REDIS_KEY, str(time.time()), nx=True):
            return
        client.set(REDIS_KEY, str(time.time()))
        return


def reset_redis_client_for_tests() -> None:
    """Clear cached Redis client (pytest only)."""
    global _redis_client
    _redis_client = None
