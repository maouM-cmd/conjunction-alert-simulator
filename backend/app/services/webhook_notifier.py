"""Webhook alert notification stub (generic POST)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import httpx

from backend.app.services.conjunction import ConjunctionEvent
from backend.app.services.tle_parser import ParsedTle

logger = logging.getLogger(__name__)

DEFAULT_PC_THRESHOLD = 1e-5
WEBHOOK_TIMEOUT_SEC = 10.0


@dataclass(frozen=True)
class WebhookResult:
    sent: bool
    alert_count: int
    degraded: bool
    message: str


def _webhook_url() -> str | None:
    url = os.environ.get("ALERT_WEBHOOK_URL", "").strip()
    return url or None


def _pc_threshold() -> float:
    raw = os.environ.get("ALERT_PC_THRESHOLD", "").strip()
    if not raw:
        return DEFAULT_PC_THRESHOLD
    try:
        return max(float(raw), 0.0)
    except ValueError:
        return DEFAULT_PC_THRESHOLD


def _filter_alert_events(events: list[ConjunctionEvent]) -> list[ConjunctionEvent]:
    threshold = _pc_threshold()
    return [
        e
        for e in events
        if e.risk_level in ("high", "medium") and e.pc >= threshold
    ]


def _build_payload(satellite: ParsedTle, events: list[ConjunctionEvent]) -> dict:
    return {
        "source": "cas",
        "satellite": {
            "name": satellite.name,
            "norad_id": satellite.norad_id,
        },
        "alerts": [
            {
                "debris_norad_id": e.debris_norad_id,
                "debris_name": e.debris_name,
                "tca": e.tca.isoformat(),
                "pc": e.pc,
                "risk_level": e.risk_level,
                "miss_distance_km": e.miss_distance_km,
            }
            for e in events
        ],
    }


def _post_payload(payload: dict) -> WebhookResult:
    url = _webhook_url()
    if not url:
        return WebhookResult(
            sent=False,
            alert_count=len(payload.get("alerts", [])),
            degraded=False,
            message="ALERT_WEBHOOK_URL が未設定です。",
        )

    try:
        with httpx.Client(timeout=WEBHOOK_TIMEOUT_SEC) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
        return WebhookResult(
            sent=True,
            alert_count=len(payload.get("alerts", [])),
            degraded=False,
            message=f"Webhook POST 成功 ({response.status_code})。",
        )
    except httpx.HTTPError as exc:
        logger.warning("Webhook POST 失敗: %s", exc)
        return WebhookResult(
            sent=False,
            alert_count=len(payload.get("alerts", [])),
            degraded=True,
            message=f"Webhook POST 失敗: {exc}",
        )


def notify_conjunction_events(
    satellite: ParsedTle,
    events: list[ConjunctionEvent],
) -> WebhookResult:
    """POST high/medium risk events above Pc threshold to ALERT_WEBHOOK_URL."""
    url = _webhook_url()
    if not url:
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message="ALERT_WEBHOOK_URL が未設定です。",
        )

    alerts = _filter_alert_events(events)
    if not alerts:
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message="通知対象イベントがありません。",
        )

    payload = _build_payload(satellite, alerts)
    return _post_payload(payload)


def send_test_webhook() -> WebhookResult:
    """Send a test ping to ALERT_WEBHOOK_URL."""
    url = _webhook_url()
    if not url:
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message="ALERT_WEBHOOK_URL が未設定です。",
        )

    payload = {
        "source": "cas",
        "test": True,
        "message": "CAS webhook test ping",
    }
    return _post_payload(payload)
