"""Webhook alert notification (generic JSON, Slack Incoming Webhook, or Slack Bot)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import httpx

from backend.app.services.analysis import ConjunctionAnalysisResult
from backend.app.services.conjunction import ConjunctionEvent
from backend.app.services.tle_parser import ParsedTle

logger = logging.getLogger(__name__)

DEFAULT_PC_THRESHOLD = 1e-5
WEBHOOK_TIMEOUT_SEC = 10.0
SLACK_TEXT_MAX_LEN = 4096
SLACK_API_POST_MESSAGE = "https://slack.com/api/chat.postMessage"
VALID_WEBHOOK_FORMATS = ("generic", "slack", "slack_bot")


@dataclass(frozen=True)
class WebhookResult:
    sent: bool
    alert_count: int
    degraded: bool
    message: str


def _webhook_url() -> str | None:
    url = os.environ.get("ALERT_WEBHOOK_URL", "").strip()
    return url or None


def _slack_bot_token() -> str | None:
    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    return token or None


def _slack_channel_id() -> str | None:
    channel = os.environ.get("SLACK_CHANNEL_ID", "").strip()
    return channel or None


def _webhook_format() -> str:
    fmt = os.environ.get("ALERT_WEBHOOK_FORMAT", "generic").strip().lower()
    return fmt if fmt in VALID_WEBHOOK_FORMATS else "generic"


def _is_delivery_configured() -> bool:
    if _webhook_format() == "slack_bot":
        return bool(_slack_bot_token() and _slack_channel_id())
    return bool(_webhook_url())


def _delivery_not_configured_message() -> str:
    if _webhook_format() == "slack_bot":
        if not _slack_bot_token():
            return "SLACK_BOT_TOKEN が未設定です。"
        return "SLACK_CHANNEL_ID が未設定です。"
    return "ALERT_WEBHOOK_URL が未設定です。"


def get_alert_delivery_format() -> str | None:
    """Configured delivery format, or None when credentials are missing."""
    if not _is_delivery_configured():
        return None
    return _webhook_format()


def is_alert_delivery_configured() -> bool:
    return _is_delivery_configured()


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


def _format_pc(pc: float) -> str:
    if pc >= 0.0001:
        return f"{pc:.2e}"
    if pc == 0:
        return "0"
    return f"{pc:.1e}"


def _alert_line(satellite: ParsedTle, event: ConjunctionEvent) -> str:
    return (
        f"• {satellite.name} (NORAD {satellite.norad_id}) vs "
        f"{event.debris_name} (NORAD {event.debris_norad_id}): "
        f"Pc={_format_pc(event.pc)} / miss={event.miss_distance_km:.2f} km / "
        f"TCA={event.tca.isoformat()} / {event.risk_level}"
    )


def _build_generic_payload(satellite: ParsedTle, events: list[ConjunctionEvent]) -> dict:
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


def _build_batch_generic_payload(
    alerts: list[tuple[ParsedTle, ConjunctionEvent]],
    satellite_count: int,
) -> dict:
    return {
        "source": "cas",
        "batch": True,
        "satellite_count": satellite_count,
        "alerts": [
            {
                "satellite_name": sat.name,
                "satellite_norad_id": sat.norad_id,
                "debris_norad_id": e.debris_norad_id,
                "debris_name": e.debris_name,
                "tca": e.tca.isoformat(),
                "pc": e.pc,
                "risk_level": e.risk_level,
                "miss_distance_km": e.miss_distance_km,
            }
            for sat, e in alerts
        ],
    }


def _build_slack_text(
    header: str,
    lines: list[str],
) -> dict:
    body = header + "\n" + "\n".join(lines) if lines else header
    if len(body) > SLACK_TEXT_MAX_LEN:
        body = body[: SLACK_TEXT_MAX_LEN - 20] + "\n…(truncated)"
    return {"text": body}


def _serialize_payload(
    satellite: ParsedTle | None,
    events: list[ConjunctionEvent],
    *,
    batch_alerts: list[tuple[ParsedTle, ConjunctionEvent]] | None = None,
    satellite_count: int = 1,
) -> dict:
    fmt = _webhook_format()
    if fmt in ("slack", "slack_bot"):
        if batch_alerts is not None:
            lines = [_alert_line(sat, e) for sat, e in batch_alerts]
            header = f"*CAS batch alert* — {len(batch_alerts)} event(s) across {satellite_count} satellite(s)"
            return _build_slack_text(header, lines)
        assert satellite is not None
        lines = [_alert_line(satellite, e) for e in events]
        header = f"*CAS conjunction alert* — {satellite.name} (NORAD {satellite.norad_id})"
        return _build_slack_text(header, lines)

    if batch_alerts is not None:
        return _build_batch_generic_payload(batch_alerts, satellite_count)
    assert satellite is not None
    return _build_generic_payload(satellite, events)


def _post_slack_bot(text: str, alert_count: int) -> WebhookResult:
    token = _slack_bot_token()
    channel = _slack_channel_id()
    if not token:
        return WebhookResult(
            sent=False,
            alert_count=alert_count,
            degraded=False,
            message="SLACK_BOT_TOKEN が未設定です。",
        )
    if not channel:
        return WebhookResult(
            sent=False,
            alert_count=alert_count,
            degraded=False,
            message="SLACK_CHANNEL_ID が未設定です。",
        )

    try:
        with httpx.Client(timeout=WEBHOOK_TIMEOUT_SEC) as client:
            response = client.post(
                SLACK_API_POST_MESSAGE,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"channel": channel, "text": text},
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                error = data.get("error", "unknown_error")
                return WebhookResult(
                    sent=False,
                    alert_count=alert_count,
                    degraded=True,
                    message=f"Slack API エラー: {error}",
                )
            return WebhookResult(
                sent=True,
                alert_count=alert_count,
                degraded=False,
                message="Slack chat.postMessage 成功。",
            )
    except httpx.HTTPError as exc:
        logger.warning("Slack chat.postMessage 失敗: %s", exc)
        return WebhookResult(
            sent=False,
            alert_count=alert_count,
            degraded=True,
            message=f"Slack chat.postMessage 失敗: {exc}",
        )


def _post_payload(payload: dict, alert_count: int) -> WebhookResult:
    if _webhook_format() == "slack_bot":
        text = payload.get("text")
        if not isinstance(text, str):
            return WebhookResult(
                sent=False,
                alert_count=alert_count,
                degraded=True,
                message="Slack Bot 形式のペイロードが不正です。",
            )
        return _post_slack_bot(text, alert_count)

    url = _webhook_url()
    if not url:
        return WebhookResult(
            sent=False,
            alert_count=alert_count,
            degraded=False,
            message="ALERT_WEBHOOK_URL が未設定です。",
        )

    try:
        with httpx.Client(timeout=WEBHOOK_TIMEOUT_SEC) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
        return WebhookResult(
            sent=True,
            alert_count=alert_count,
            degraded=False,
            message=f"Webhook POST 成功 ({response.status_code})。",
        )
    except httpx.HTTPError as exc:
        logger.warning("Webhook POST 失敗: %s", exc)
        return WebhookResult(
            sent=False,
            alert_count=alert_count,
            degraded=True,
            message=f"Webhook POST 失敗: {exc}",
        )


def notify_conjunction_events(
    satellite: ParsedTle,
    events: list[ConjunctionEvent],
) -> WebhookResult:
    """POST high/medium risk events above Pc threshold to configured alert delivery."""
    if not _is_delivery_configured():
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message=_delivery_not_configured_message(),
        )

    alerts = _filter_alert_events(events)
    if not alerts:
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message="通知対象イベントがありません。",
        )

    payload = _serialize_payload(satellite, alerts)
    return _post_payload(payload, len(alerts))


def notify_batch_fleet_events(results: list[ConjunctionAnalysisResult]) -> WebhookResult:
    """POST aggregated high/medium alerts from batch analysis as one fleet summary."""
    if not _is_delivery_configured():
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message=_delivery_not_configured_message(),
        )

    batch_alerts: list[tuple[ParsedTle, ConjunctionEvent]] = []
    for result in results:
        for event in _filter_alert_events(result.events):
            batch_alerts.append((result.satellite, event))

    if not batch_alerts:
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message="通知対象イベントがありません。",
        )

    payload = _serialize_payload(
        None,
        [],
        batch_alerts=batch_alerts,
        satellite_count=len(results),
    )
    return _post_payload(payload, len(batch_alerts))


def send_test_webhook() -> WebhookResult:
    """Send a test ping to the configured alert delivery."""
    if not _is_delivery_configured():
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message=_delivery_not_configured_message(),
        )

    fmt = _webhook_format()
    if fmt in ("slack", "slack_bot"):
        payload = {"text": "*CAS* webhook test ping"}
    else:
        payload = {
            "source": "cas",
            "test": True,
            "message": "CAS webhook test ping",
        }
    return _post_payload(payload, 0)
