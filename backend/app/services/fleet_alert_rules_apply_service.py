"""Prometheus fleet alert rules file apply (Phase 10AG / 10AH / 10AI)."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

RELOAD_TIMEOUT_SEC = 10.0


@dataclass(frozen=True)
class FleetAlertRulesApplyResult:
    applied: bool
    path: str | None
    message: str
    reloaded: bool = False
    reload_message: str | None = None
    reload_queued: bool = False


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


def queue_prometheus_reload() -> bool:
    try:
        from backend.app.tasks.alertmanager_tasks import prometheus_reload_task

        prometheus_reload_task.delay()
        return True
    except Exception as exc:
        logger.warning("Prometheus reload Celery enqueue failed: %s", exc)
        return False


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
    if not reloaded and prometheus_reload_celery_fallback_enabled():
        reload_queued = queue_prometheus_reload()
        if reload_queued:
            reload_message = f"{reload_message} Celery フォールバックに enqueue しました。"

    return FleetAlertRulesApplyResult(
        applied=True,
        path=str(target),
        message=f"ルールを {target} に書き込みました。",
        reloaded=reloaded,
        reload_message=reload_message,
        reload_queued=reload_queued,
    )
