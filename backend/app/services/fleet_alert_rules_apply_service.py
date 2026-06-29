"""Prometheus fleet alert rules file apply (Phase 10AG / 10AH)."""

from __future__ import annotations

import logging
import os
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


def prometheus_fleet_rules_output_path() -> str | None:
    raw = os.getenv("PROMETHEUS_FLEET_RULES_OUTPUT_PATH", "").strip()
    return raw or None


def prometheus_reload_url() -> str | None:
    raw = os.getenv("PROMETHEUS_RELOAD_URL", "").strip()
    return raw or None


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
    try:
        with httpx.Client(timeout=RELOAD_TIMEOUT_SEC) as client:
            response = client.post(url, auth=auth)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Prometheus reload failed: %s", exc)
        return False, f"Prometheus reload 失敗: {exc}"
    return True, "Prometheus reload を実行しました。"


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
    return FleetAlertRulesApplyResult(
        applied=True,
        path=str(target),
        message=f"ルールを {target} に書き込みました。",
        reloaded=reloaded,
        reload_message=reload_message,
    )
