"""Prometheus fleet alert rules file apply (Phase 10AG / 10AH / 10AI)."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from backend.app.db.session import get_redis_url, is_redis_configured

logger = logging.getLogger(__name__)

RELOAD_TIMEOUT_SEC = 10.0
_REDIS_HISTORY_KEY = "cas:prometheus:reload:history"


@dataclass(frozen=True)
class FleetAlertRulesApplyResult:
    applied: bool
    path: str | None
    message: str
    reloaded: bool = False
    reload_message: str | None = None
    reload_queued: bool = False
    reload_task_id: str | None = None


_enqueued_reload_task_ids: set[str] = set()


@dataclass(frozen=True)
class ReloadHistoryEntry:
    task_id: str | None
    source: str
    enqueued_at: datetime
    state: str
    reloaded: bool
    message: str


_reload_history: list[ReloadHistoryEntry] = []
_redis_client = None


def prometheus_reload_history_redis_enabled() -> bool:
    if not is_redis_configured():
        return False
    raw = os.getenv("PROMETHEUS_RELOAD_HISTORY_REDIS_ENABLED", "").strip().lower()
    if raw:
        return raw in ("1", "true", "yes", "on")
    return True


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if not prometheus_reload_history_redis_enabled():
        return None
    url = get_redis_url()
    if not url:
        return None
    try:
        import redis

        _redis_client = redis.from_url(url, decode_responses=True)
        _redis_client.ping()
        return _redis_client
    except Exception as exc:
        logger.warning("Prometheus reload history Redis unavailable: %s", exc)
        return None


def _use_reload_history_redis() -> bool:
    return _get_redis() is not None


def _entry_to_payload(entry: ReloadHistoryEntry) -> dict:
    return {
        "task_id": entry.task_id,
        "source": entry.source,
        "enqueued_at": entry.enqueued_at.isoformat(),
        "state": entry.state,
        "reloaded": entry.reloaded,
        "message": entry.message,
    }


def _entry_from_payload(payload: dict) -> ReloadHistoryEntry:
    enqueued_raw = payload.get("enqueued_at")
    if isinstance(enqueued_raw, str):
        enqueued_at = datetime.fromisoformat(enqueued_raw.replace("Z", "+00:00"))
    else:
        enqueued_at = datetime.now(timezone.utc)
    if enqueued_at.tzinfo is None:
        enqueued_at = enqueued_at.replace(tzinfo=timezone.utc)
    return ReloadHistoryEntry(
        task_id=payload.get("task_id"),
        source=str(payload.get("source") or ""),
        enqueued_at=enqueued_at,
        state=str(payload.get("state") or ""),
        reloaded=bool(payload.get("reloaded")),
        message=str(payload.get("message") or ""),
    )


def _push_reload_history_redis(entry: ReloadHistoryEntry) -> None:
    client = _get_redis()
    if client is None:
        return
    limit = prometheus_reload_history_size()
    try:
        client.lpush(_REDIS_HISTORY_KEY, json.dumps(_entry_to_payload(entry), ensure_ascii=False))
        client.ltrim(_REDIS_HISTORY_KEY, 0, limit - 1)
        ttl = prometheus_reload_history_redis_ttl_seconds()
        if ttl is not None:
            client.expire(_REDIS_HISTORY_KEY, ttl)
    except Exception as exc:
        logger.warning("Prometheus reload history Redis write failed: %s", exc)
        reset_reload_history_redis_client_for_tests()


def _load_reload_history_redis(limit: int) -> list[ReloadHistoryEntry]:
    client = _get_redis()
    if client is None:
        return []
    capped = max(min(limit, prometheus_reload_history_size()), 1)
    try:
        raw_items = client.lrange(_REDIS_HISTORY_KEY, 0, capped - 1)
    except Exception as exc:
        logger.warning("Prometheus reload history Redis read failed: %s", exc)
        reset_reload_history_redis_client_for_tests()
        return []
    entries: list[ReloadHistoryEntry] = []
    for raw in raw_items:
        try:
            entries.append(_entry_from_payload(json.loads(raw)))
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    return _filter_reload_history_by_ttl(entries)


def reset_reload_history_redis_client_for_tests() -> None:
    global _redis_client
    _redis_client = None


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def prometheus_fleet_rules_output_path() -> str | None:
    raw = os.getenv("PROMETHEUS_FLEET_RULES_OUTPUT_PATH", "").strip()
    return raw or None


def prometheus_reload_url() -> str | None:
    raw = os.getenv("PROMETHEUS_RELOAD_URL", "").strip()
    return raw or None


def prometheus_reload_max_retries() -> int:
    raw = os.getenv("PROMETHEUS_RELOAD_MAX_RETRIES", "3").strip()
    try:
        return max(int(raw), 1)
    except ValueError:
        return 3


def prometheus_reload_celery_fallback_enabled() -> bool:
    return _env_bool("PROMETHEUS_RELOAD_CELERY_FALLBACK", default=False)


def prometheus_reload_history_size() -> int:
    raw = os.getenv("PROMETHEUS_RELOAD_HISTORY_SIZE", "20").strip()
    try:
        return max(int(raw), 1)
    except ValueError:
        return 20


def prometheus_reload_history_redis_ttl_seconds() -> int | None:
    raw = os.getenv("PROMETHEUS_RELOAD_HISTORY_REDIS_TTL_SECONDS", "604800").strip().lower()
    if raw in ("0", "none", "off"):
        return None
    try:
        return max(int(raw), 1)
    except ValueError:
        return 604800


def _filter_reload_history_by_ttl(entries: list[ReloadHistoryEntry]) -> list[ReloadHistoryEntry]:
    ttl = prometheus_reload_history_redis_ttl_seconds()
    if ttl is None:
        return entries
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=ttl)
    return [entry for entry in entries if entry.enqueued_at >= cutoff]


def _record_reload_history(
    *,
    task_id: str | None,
    source: str,
    message: str,
    state: str,
    reloaded: bool,
) -> None:
    entry = ReloadHistoryEntry(
        task_id=task_id,
        source=source,
        enqueued_at=datetime.now(timezone.utc),
        state=state,
        reloaded=reloaded,
        message=message,
    )
    _reload_history.append(entry)
    limit = prometheus_reload_history_size()
    while len(_reload_history) > limit:
        _reload_history.pop(0)
    _push_reload_history_redis(entry)


def _history_entry_to_item(entry: ReloadHistoryEntry) -> dict:
    if entry.task_id:
        try:
            live = get_prometheus_reload_task_status(entry.task_id)
        except Exception:
            live = None
        if live:
            return {
                "task_id": entry.task_id,
                "source": entry.source,
                "state": live["state"],
                "reloaded": live["reloaded"],
                "message": live["message"],
                "enqueued_at": entry.enqueued_at,
            }
    return {
        "task_id": entry.task_id,
        "source": entry.source,
        "state": entry.state,
        "reloaded": entry.reloaded,
        "message": entry.message,
        "enqueued_at": entry.enqueued_at,
    }


def _reload_basic_auth() -> tuple[str, str] | None:
    user = os.getenv("PROMETHEUS_RELOAD_BASIC_AUTH_USER", "").strip()
    password = os.getenv("PROMETHEUS_RELOAD_BASIC_AUTH_PASSWORD", "").strip()
    if user and password:
        return user, password
    return None


def reload_prometheus() -> tuple[bool, str]:
    url = prometheus_reload_url()
    if url is None:
        return False, "PROMETHEUS_RELOAD_URL が未設定です。"

    auth = _reload_basic_auth()
    max_retries = prometheus_reload_max_retries()
    last_error = "unknown error"
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=RELOAD_TIMEOUT_SEC) as client:
                response = client.post(url, auth=auth)
                response.raise_for_status()
            return True, "Prometheus reload を実行しました。"
        except httpx.HTTPError as exc:
            last_error = str(exc)
            logger.warning("Prometheus reload failed (attempt %s/%s): %s", attempt + 1, max_retries, exc)
            if attempt < max_retries - 1:
                time.sleep(0.2 * (attempt + 1))
    return False, f"Prometheus reload 失敗（{max_retries} 回）: {last_error}"


def queue_prometheus_reload() -> str | None:
    try:
        from backend.app.tasks.alertmanager_tasks import prometheus_reload_task

        async_result = prometheus_reload_task.delay()
        _enqueued_reload_task_ids.add(async_result.id)
        _record_reload_history(
            task_id=async_result.id,
            source="celery",
            message="Celery reload タスクに enqueue しました。",
            state="PENDING",
            reloaded=False,
        )
        return async_result.id
    except Exception as exc:
        logger.warning("Prometheus reload Celery enqueue failed: %s", exc)
        return None


def reload_task_known(task_id: str) -> bool:
    if task_id in _enqueued_reload_task_ids:
        return True

    from backend.app.tasks.celery_app import celery_app

    backend = celery_app.backend
    if hasattr(backend, "get_key_for_task") and getattr(backend, "client", None) is not None:
        try:
            key = backend.get_key_for_task(task_id)
            return backend.client.get(key) is not None
        except Exception:
            pass
    return False


def get_prometheus_reload_task_status(task_id: str) -> dict | None:
    if not reload_task_known(task_id):
        return None

    from backend.app.tasks.celery_app import celery_app

    result = celery_app.AsyncResult(task_id)
    state = result.state or "PENDING"
    payload = result.result if isinstance(result.result, dict) else {}
    reloaded = bool(payload.get("reloaded")) if payload else False
    message = str(payload.get("message") or "")
    if state == "SUCCESS" and not message:
        message = "Prometheus reload タスクが完了しました。"
    if state == "FAILURE":
        message = str(result.result) if result.result else "Prometheus reload タスクが失敗しました。"
        reloaded = False
    if state in ("PENDING", "STARTED", "RETRY"):
        message = message or "Prometheus reload タスク実行中…"
    return {
        "task_id": task_id,
        "state": state,
        "reloaded": reloaded,
        "message": message,
    }


def record_sync_prometheus_reload(*, reloaded: bool, message: str) -> None:
    _record_reload_history(
        task_id=None,
        source="sync",
        message=message,
        state="SUCCESS" if reloaded else "FAILURE",
        reloaded=reloaded,
    )


def list_prometheus_reload_history(limit: int = 20) -> list[dict]:
    capped = max(min(limit, prometheus_reload_history_size()), 1)
    entries: list[ReloadHistoryEntry] = []
    if _use_reload_history_redis():
        entries = _load_reload_history_redis(capped)
    if not entries:
        entries = list(reversed(_reload_history[-capped:]))
    else:
        entries = _filter_reload_history_by_ttl(entries)
    return [_history_entry_to_item(entry) for entry in entries]


def clear_reload_tasks_for_tests() -> None:
    _enqueued_reload_task_ids.clear()
    _reload_history.clear()
    client = _get_redis()
    if client is not None:
        try:
            client.delete(_REDIS_HISTORY_KEY)
        except Exception:
            pass
    reset_reload_history_redis_client_for_tests()


def apply_fleet_alert_rules(content: str, *, format: str) -> FleetAlertRulesApplyResult:
    path = prometheus_fleet_rules_output_path()
    if path is None:
        return FleetAlertRulesApplyResult(
            applied=False,
            path=None,
            message="PROMETHEUS_FLEET_RULES_OUTPUT_PATH が未設定です。ダウンロードして手動適用してください。",
        )

    target = Path(path)
    parent = target.parent
    if not parent.exists():
        return FleetAlertRulesApplyResult(
            applied=False,
            path=str(target),
            message=f"出力先ディレクトリが存在しません: {parent}",
        )

    suffix = ".json" if format.lower() == "json" else ".yaml"
    if target.suffix != suffix:
        target = target.with_suffix(suffix)
    tmp_path = target.with_name(target.name + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, target)

    reloaded, reload_message = reload_prometheus()
    reload_queued = False
    reload_task_id = None
    if not reloaded and prometheus_reload_celery_fallback_enabled():
        reload_task_id = queue_prometheus_reload()
        reload_queued = reload_task_id is not None
        if reload_queued:
            reload_message = f"{reload_message} Celery フォールバックに enqueue しました。"

    return FleetAlertRulesApplyResult(
        applied=True,
        path=str(target),
        message=f"ルールを {target} に書き込みました。",
        reloaded=reloaded,
        reload_message=reload_message,
        reload_queued=reload_queued,
        reload_task_id=reload_task_id,
    )
