"""Extended health checks (Phase 9E)."""

from __future__ import annotations

from typing import Literal

from sqlalchemy import text

from backend.app.db.session import get_engine, get_redis_url, is_database_configured, is_redis_configured

CheckStatus = Literal["ok", "error", "skipped"]


def _check_postgres() -> CheckStatus:
    if not is_database_configured():
        return "skipped"
    engine = get_engine()
    if engine is None:
        return "error"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"


def _check_redis() -> CheckStatus:
    if not is_redis_configured():
        return "skipped"
    url = get_redis_url()
    if not url:
        return "skipped"
    try:
        import redis

        client = redis.from_url(url, decode_responses=True)
        client.ping()
        return "ok"
    except Exception:
        return "error"


def _check_worker() -> CheckStatus:
    if not is_redis_configured():
        return "skipped"
    try:
        from backend.app.tasks.celery_app import celery_app

        inspect = celery_app.control.inspect(timeout=1.0)
        if inspect is None:
            return "error"
        ping = inspect.ping()
        if ping:
            return "ok"
        return "error"
    except Exception:
        return "error"


def run_health_checks() -> dict[str, CheckStatus]:
    return {
        "postgres": _check_postgres(),
        "redis": _check_redis(),
        "worker": _check_worker(),
    }


def aggregate_status(checks: dict[str, CheckStatus]) -> Literal["ok", "degraded"]:
    configured = [v for v in checks.values() if v != "skipped"]
    if not configured:
        return "ok"
    if all(v == "ok" for v in configured):
        return "ok"
    return "degraded"
