"""Alertmanager alert push on fleet breach state changes (Phase 10S)."""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from backend.app.services import fleet_alert_metrics_service

logger = logging.getLogger(__name__)

PUSH_TIMEOUT_SEC = 10.0
ALERT_OPEN = "CASFleetOpenAlertsHigh"
ALERT_HIGH_RISK = "CASFleetHighRiskOpenAlerts"

_last_breach_state: dict[tuple[str, str], bool] = {}


@dataclass(frozen=True)
class PushResult:
    sent: bool
    message: str


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def alertmanager_push_enabled() -> bool:
    return _env_bool("ALERTMANAGER_PUSH_ENABLED", default=False)


def alertmanager_push_configured() -> bool:
    return alertmanager_push_enabled() and bool(alertmanager_url())


def alertmanager_url() -> str | None:
    raw = os.environ.get("ALERTMANAGER_URL", "").strip()
    if not raw:
        return None
    return raw.rstrip("/")


def _basic_auth() -> tuple[str, str] | None:
    user = os.environ.get("ALERTMANAGER_BASIC_AUTH_USER", "").strip()
    password = os.environ.get("ALERTMANAGER_BASIC_AUTH_PASSWORD", "").strip()
    if user and password:
        return user, password
    return None


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _resolve_ends_at() -> str:
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    return past.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def build_alert_payload(
    *,
    alertname: str,
    fleet_id: uuid.UUID,
    fleet_name: str,
    severity: str,
    summary: str,
    firing: bool,
) -> dict[str, Any]:
    labels: dict[str, str] = {
        "alertname": alertname,
        "fleet_id": str(fleet_id),
        "severity": severity,
    }
    payload: dict[str, Any] = {
        "labels": labels,
        "annotations": {"summary": summary},
    }
    if firing:
        payload["startsAt"] = _utcnow_iso()
    else:
        payload["endsAt"] = _resolve_ends_at()
    return payload


def build_test_alert() -> dict[str, Any]:
    return {
        "labels": {
            "alertname": "CASTestAlert",
            "severity": "info",
            "source": "conjunction-alert-simulator",
        },
        "annotations": {
            "summary": "CAS Alertmanager connectivity test",
        },
        "startsAt": _utcnow_iso(),
    }


def push_alerts(alerts: list[dict[str, Any]]) -> PushResult:
    url = alertmanager_url()
    if not url:
        return PushResult(sent=False, message="ALERTMANAGER_URL が未設定です。")
    endpoint = f"{url}/api/v2/alerts"
    auth = _basic_auth()
    try:
        with httpx.Client(timeout=PUSH_TIMEOUT_SEC) as client:
            response = client.post(endpoint, json=alerts, auth=auth)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Alertmanager push failed: %s", exc)
        return PushResult(sent=False, message=f"Alertmanager push 失敗: {exc}")
    return PushResult(sent=True, message=f"{len(alerts)} 件を Alertmanager に送信しました。")


def send_test_push() -> PushResult:
    if not alertmanager_push_enabled():
        return PushResult(sent=False, message="Alertmanager push は無効です（ALERTMANAGER_PUSH_ENABLED）。")
    return push_alerts([build_test_alert()])


def _is_open_breach(open_count: int) -> bool:
    return open_count > fleet_alert_metrics_service.fleet_open_alert_threshold()


def _is_high_risk_breach(high_open_count: int) -> bool:
    return high_open_count >= fleet_alert_metrics_service.fleet_high_risk_open_threshold()


def sync_breaches(
    counts: dict[uuid.UUID, dict[str, int]],
    risk_counts: dict[uuid.UUID, dict[str, dict[str, int]]],
    fleet_names: dict[uuid.UUID, str],
) -> None:
    if not alertmanager_push_configured():
        return
    if not fleet_alert_metrics_service.fleet_alert_metrics_enabled():
        return

    to_push: list[dict[str, Any]] = []
    fleet_ids = set(counts) | set(risk_counts) | set(fleet_names)

    for fleet_id in fleet_ids:
        fleet_name = fleet_names.get(fleet_id, str(fleet_id))
        status_counts = counts.get(fleet_id, {})
        risk_status = risk_counts.get(fleet_id, {})
        open_count = status_counts.get("open", 0)
        high_open = risk_status.get("high", {}).get("open", 0)

        breach_specs = [
            (
                ALERT_OPEN,
                _is_open_breach(open_count),
                "warning",
                f"Fleet {fleet_name} has {open_count} open alerts (threshold exceeded)",
            ),
            (
                ALERT_HIGH_RISK,
                _is_high_risk_breach(high_open),
                "critical",
                f"Fleet {fleet_name} has {high_open} high-risk open alerts",
            ),
        ]

        for alertname, is_breaching, severity, summary in breach_specs:
            key = (str(fleet_id), alertname)
            previous = _last_breach_state.get(key, False)
            if is_breaching == previous:
                continue
            _last_breach_state[key] = is_breaching
            to_push.append(
                build_alert_payload(
                    alertname=alertname,
                    fleet_id=fleet_id,
                    fleet_name=fleet_name,
                    severity=severity,
                    summary=summary,
                    firing=is_breaching,
                )
            )

    if to_push:
        push_alerts(to_push)


def reset_breach_state_for_tests() -> None:
    _last_breach_state.clear()
