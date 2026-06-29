"""Webhook alert notification (generic JSON, Slack, Slack Bot, SMTP, or PagerDuty)."""

from __future__ import annotations

import logging
import os
import smtplib
import uuid
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Literal

import httpx

from backend.app.services.analysis import ConjunctionAnalysisResult
from backend.app.services.conjunction import ConjunctionEvent
from backend.app.services.tle_parser import ParsedTle

logger = logging.getLogger(__name__)

DEFAULT_PC_THRESHOLD = 1e-5
DEFAULT_SMTP_PORT = 587
WEBHOOK_TIMEOUT_SEC = 10.0
SLACK_TEXT_MAX_LEN = 4096
SLACK_API_POST_MESSAGE = "https://slack.com/api/chat.postMessage"
PAGERDUTY_EVENTS_URL = "https://events.pagerduty.com/v2/enqueue"
PAGERDUTY_SOURCE = "conjunction-alert-simulator"
PagerDutyEventAction = Literal["trigger", "acknowledge", "resolve"]
VALID_WEBHOOK_FORMATS = ("generic", "slack", "slack_bot", "smtp", "pagerduty")


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


def _smtp_host() -> str | None:
    host = os.environ.get("SMTP_HOST", "").strip()
    return host or None


def _smtp_port() -> int:
    raw = os.environ.get("SMTP_PORT", "").strip()
    if not raw:
        return DEFAULT_SMTP_PORT
    try:
        return max(int(raw), 1)
    except ValueError:
        return DEFAULT_SMTP_PORT


def _smtp_from() -> str | None:
    addr = os.environ.get("SMTP_FROM", "").strip()
    return addr or None


def _smtp_to() -> str | None:
    addr = os.environ.get("SMTP_TO", "").strip()
    return addr or None


def _smtp_user() -> str | None:
    user = os.environ.get("SMTP_USER", "").strip()
    return user or None


def _smtp_password() -> str | None:
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    return password or None


def _smtp_use_tls() -> bool:
    raw = os.environ.get("SMTP_USE_TLS", "true").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _pagerduty_routing_key() -> str | None:
    key = os.environ.get("PAGERDUTY_ROUTING_KEY", "").strip()
    return key or None


def pagerduty_lifecycle_enabled() -> bool:
    raw = os.environ.get("PAGERDUTY_LIFECYCLE_ENABLED", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def pagerduty_dedup_key(alert_id: uuid.UUID) -> str:
    return f"cas-alert-{alert_id}"


def _webhook_format() -> str:
    fmt = os.environ.get("ALERT_WEBHOOK_FORMAT", "generic").strip().lower()
    return fmt if fmt in VALID_WEBHOOK_FORMATS else "generic"


def _is_smtp_configured() -> bool:
    return bool(_smtp_host() and _smtp_from() and _smtp_to())


def _is_delivery_configured() -> bool:
    fmt = _webhook_format()
    if fmt == "slack_bot":
        return bool(_slack_bot_token() and _slack_channel_id())
    if fmt == "smtp":
        return _is_smtp_configured()
    if fmt == "pagerduty":
        return bool(_pagerduty_routing_key())
    return bool(_webhook_url())


def _delivery_not_configured_message() -> str:
    fmt = _webhook_format()
    if fmt == "slack_bot":
        if not _slack_bot_token():
            return "SLACK_BOT_TOKEN が未設定です。"
        return "SLACK_CHANNEL_ID が未設定です。"
    if fmt == "smtp":
        if not _smtp_host():
            return "SMTP_HOST が未設定です。"
        if not _smtp_from():
            return "SMTP_FROM が未設定です。"
        return "SMTP_TO が未設定です。"
    if fmt == "pagerduty":
        return "PAGERDUTY_ROUTING_KEY が未設定です。"
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


def filter_alert_events(events: list[ConjunctionEvent]) -> list[ConjunctionEvent]:
    threshold = _pc_threshold()
    return [
        e
        for e in events
        if e.risk_level in ("high", "medium") and e.pc >= threshold
    ]


def _filter_alert_events(events: list[ConjunctionEvent]) -> list[ConjunctionEvent]:
    return filter_alert_events(events)


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


def _build_text_body(header: str, lines: list[str]) -> str:
    body = header + "\n" + "\n".join(lines) if lines else header
    if len(body) > SLACK_TEXT_MAX_LEN:
        body = body[: SLACK_TEXT_MAX_LEN - 20] + "\n…(truncated)"
    return body


def _build_slack_text(header: str, lines: list[str]) -> dict:
    return {"text": _build_text_body(header, lines)}


def _build_email_payload(subject: str, header: str, lines: list[str]) -> dict:
    return {"subject": subject, "text": _build_text_body(header, lines)}


def _risk_severity(risk_level: str) -> str:
    if risk_level == "high":
        return "error"
    if risk_level == "medium":
        return "warning"
    return "info"


def _max_severity_from_risk_levels(risk_levels: list[str]) -> str:
    if "high" in risk_levels:
        return "error"
    if "medium" in risk_levels:
        return "warning"
    return "info"


def _build_pagerduty_enqueue(
    summary: str,
    severity: str,
    custom_details: dict,
    *,
    dedup_key: str | None = None,
    event_action: PagerDutyEventAction = "trigger",
) -> dict:
    routing_key = _pagerduty_routing_key()
    body: dict = {
        "routing_key": routing_key or "",
        "event_action": event_action,
        "payload": {
            "summary": summary[:1024],
            "severity": severity,
            "source": PAGERDUTY_SOURCE,
            "custom_details": custom_details,
        },
    }
    if dedup_key:
        body["dedup_key"] = dedup_key
    return body


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

    if fmt == "smtp":
        if batch_alerts is not None:
            lines = [_alert_line(sat, e) for sat, e in batch_alerts]
            header = (
                f"CAS batch alert — {len(batch_alerts)} event(s) across "
                f"{satellite_count} satellite(s)"
            )
            return _build_email_payload("CAS batch alert", header, lines)
        assert satellite is not None
        lines = [_alert_line(satellite, e) for e in events]
        header = f"CAS conjunction alert — {satellite.name} (NORAD {satellite.norad_id})"
        return _build_email_payload("CAS conjunction alert", header, lines)

    if fmt == "pagerduty":
        if batch_alerts is not None:
            lines = [_alert_line(sat, e) for sat, e in batch_alerts]
            header = (
                f"CAS batch alert — {len(batch_alerts)} event(s) across "
                f"{satellite_count} satellite(s)"
            )
            severity = _max_severity_from_risk_levels([e.risk_level for _, e in batch_alerts])
            details = _build_batch_generic_payload(batch_alerts, satellite_count)
            return _build_pagerduty_enqueue(header, severity, details)
        assert satellite is not None
        lines = [_alert_line(satellite, e) for e in events]
        header = f"CAS conjunction alert — {satellite.name} (NORAD {satellite.norad_id})"
        severity = _max_severity_from_risk_levels([e.risk_level for e in events])
        details = _build_generic_payload(satellite, events)
        return _build_pagerduty_enqueue(header, severity, details)

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


def _send_smtp(subject: str, body: str, alert_count: int) -> WebhookResult:
    host = _smtp_host()
    from_addr = _smtp_from()
    to_addr = _smtp_to()
    if not host:
        return WebhookResult(
            sent=False,
            alert_count=alert_count,
            degraded=False,
            message="SMTP_HOST が未設定です。",
        )
    if not from_addr:
        return WebhookResult(
            sent=False,
            alert_count=alert_count,
            degraded=False,
            message="SMTP_FROM が未設定です。",
        )
    if not to_addr:
        return WebhookResult(
            sent=False,
            alert_count=alert_count,
            degraded=False,
            message="SMTP_TO が未設定です。",
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_addr
    message["To"] = to_addr
    message.set_content(body)

    try:
        with smtplib.SMTP(host, _smtp_port(), timeout=WEBHOOK_TIMEOUT_SEC) as smtp:
            if _smtp_use_tls():
                smtp.starttls()
            user = _smtp_user()
            password = _smtp_password()
            if user and password:
                smtp.login(user, password)
            smtp.send_message(message)
        return WebhookResult(
            sent=True,
            alert_count=alert_count,
            degraded=False,
            message="SMTP 送信成功。",
        )
    except smtplib.SMTPException as exc:
        logger.warning("SMTP 送信失敗: %s", exc)
        return WebhookResult(
            sent=False,
            alert_count=alert_count,
            degraded=True,
            message=f"SMTP 送信失敗: {exc}",
        )


def _merge_webhook_results(results: list[WebhookResult], alert_count: int) -> WebhookResult:
    if not results:
        return WebhookResult(
            sent=False,
            alert_count=alert_count,
            degraded=False,
            message="通知対象イベントがありません。",
        )
    sent = any(result.sent for result in results)
    degraded = any(result.degraded for result in results)
    messages = [result.message for result in results if result.message]
    return WebhookResult(
        sent=sent,
        alert_count=alert_count,
        degraded=degraded,
        message=messages[-1] if messages else "PagerDuty Events API 完了。",
    )


def _alert_to_parsed_pair(alert) -> tuple[ParsedTle, ConjunctionEvent] | None:
    from backend.app.db.models import ConjunctionAlert

    if not isinstance(alert, ConjunctionAlert):
        return None
    satellite = alert.satellite
    if satellite is None:
        return None
    sat = ParsedTle(
        name=satellite.name,
        line1="1 00000U          00000.00000000  .00000000  00000+0  00000+0 0  9999",
        line2="2 00000   0.0000   0.0000 0000000   0.0000   0.0000  0.00000000000000",
        norad_id=satellite.norad_id,
    )
    event = ConjunctionEvent(
        debris_norad_id=alert.debris_norad_id,
        debris_name=alert.debris_name,
        debris_tle="",
        tca=alert.tca,
        miss_distance_km=alert.miss_distance_km,
        relative_velocity_kms=0.0,
        risk_level=alert.risk_level,
        pc=alert.pc,
    )
    return sat, event


def _notify_pagerduty_per_alert_triggers(alerts: list) -> WebhookResult:
    results: list[WebhookResult] = []
    count = 0
    for alert in alerts:
        pair = _alert_to_parsed_pair(alert)
        if pair is None:
            continue
        sat, event = pair
        severity = _max_severity_from_risk_levels([event.risk_level])
        details = _build_generic_payload(sat, [event])
        details["alert_id"] = str(alert.id)
        payload = _build_pagerduty_enqueue(
            f"CAS new alert — {sat.name} vs {event.debris_name}",
            severity,
            details,
            dedup_key=pagerduty_dedup_key(alert.id),
            event_action="trigger",
        )
        results.append(_post_pagerduty(payload, 1))
        count += 1
    return _merge_webhook_results(results, count)


def notify_pagerduty_lifecycle(alert, event_action: PagerDutyEventAction) -> WebhookResult:
    """Send PagerDuty acknowledge/resolve for a persisted alert (Phase 10O)."""
    from backend.app.db.models import ConjunctionAlert

    if _webhook_format() != "pagerduty" or not pagerduty_lifecycle_enabled():
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message="PagerDuty lifecycle は無効です。",
        )
    if not _is_delivery_configured():
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message=_delivery_not_configured_message(),
        )
    if not isinstance(alert, ConjunctionAlert):
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message="通知対象が不正です。",
        )

    satellite = alert.satellite
    sat_name = satellite.name if satellite else "UNKNOWN"
    summary = (
        f"CAS alert {event_action} — {sat_name} vs {alert.debris_name} "
        f"(status={alert.status})"
    )
    payload = _build_pagerduty_enqueue(
        summary,
        "info",
        {
            "alert_id": str(alert.id),
            "status": alert.status,
            "event_action": event_action,
        },
        dedup_key=pagerduty_dedup_key(alert.id),
        event_action=event_action,
    )
    return _post_pagerduty(payload, 1)


def notify_pagerduty_lifecycle_for_status(alert, new_status: str) -> None:
    if new_status == "acknowledged":
        result = notify_pagerduty_lifecycle(alert, "acknowledge")
    elif new_status in ("closed", "false_positive"):
        result = notify_pagerduty_lifecycle(alert, "resolve")
    else:
        return
    if not result.sent and result.degraded:
        logger.warning("PagerDuty lifecycle 送信失敗: %s", result.message)


def _post_pagerduty(payload: dict, alert_count: int) -> WebhookResult:
    routing_key = _pagerduty_routing_key()
    if not routing_key:
        return WebhookResult(
            sent=False,
            alert_count=alert_count,
            degraded=False,
            message="PAGERDUTY_ROUTING_KEY が未設定です。",
        )

    body = dict(payload)
    body["routing_key"] = routing_key

    try:
        with httpx.Client(timeout=WEBHOOK_TIMEOUT_SEC) as client:
            response = client.post(PAGERDUTY_EVENTS_URL, json=body)
            response.raise_for_status()
        return WebhookResult(
            sent=True,
            alert_count=alert_count,
            degraded=False,
            message="PagerDuty Events API 成功。",
        )
    except httpx.HTTPError as exc:
        logger.warning("PagerDuty Events API 失敗: %s", exc)
        return WebhookResult(
            sent=False,
            alert_count=alert_count,
            degraded=True,
            message=f"PagerDuty Events API 失敗: {exc}",
        )


def _post_payload(payload: dict, alert_count: int) -> WebhookResult:
    fmt = _webhook_format()
    if fmt == "slack_bot":
        text = payload.get("text")
        if not isinstance(text, str):
            return WebhookResult(
                sent=False,
                alert_count=alert_count,
                degraded=True,
                message="Slack Bot 形式のペイロードが不正です。",
            )
        return _post_slack_bot(text, alert_count)

    if fmt == "smtp":
        subject = payload.get("subject")
        text = payload.get("text")
        if not isinstance(subject, str) or not isinstance(text, str):
            return WebhookResult(
                sent=False,
                alert_count=alert_count,
                degraded=True,
                message="SMTP 形式のペイロードが不正です。",
            )
        return _send_smtp(subject, text, alert_count)

    if fmt == "pagerduty":
        return _post_pagerduty(payload, alert_count)

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


def notify_new_alerts(alerts: list) -> WebhookResult:
    """POST webhook for newly opened persisted alerts (Phase 9C screening path)."""
    from backend.app.db.models import ConjunctionAlert

    if not _is_delivery_configured():
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message=_delivery_not_configured_message(),
        )
    if not alerts:
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message="通知対象イベントがありません。",
        )

    batch_alerts: list[tuple[ParsedTle, ConjunctionEvent]] = []
    for alert in alerts:
        pair = _alert_to_parsed_pair(alert)
        if pair is not None:
            batch_alerts.append(pair)

    if not batch_alerts:
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message="通知対象イベントがありません。",
        )

    if _webhook_format() == "pagerduty" and pagerduty_lifecycle_enabled():
        return _notify_pagerduty_per_alert_triggers(alerts)

    payload = _serialize_payload(
        None,
        [],
        batch_alerts=batch_alerts,
        satellite_count=len({a.satellite_id for a in alerts if isinstance(a, ConjunctionAlert)}),
    )
    return _post_payload(payload, len(batch_alerts))


def notify_pc_escalation(alert, refinement) -> WebhookResult:
    """POST escalation notification when refined Pc exceeds threshold (Phase 10E)."""
    from backend.app.db.models import AlertPcRefinement, ConjunctionAlert

    if not _is_delivery_configured():
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message=_delivery_not_configured_message(),
        )
    if not isinstance(alert, ConjunctionAlert) or not isinstance(refinement, AlertPcRefinement):
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message="通知対象が不正です。",
        )

    satellite = alert.satellite
    if satellite is None:
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message="衛星情報がありません。",
        )

    method_label = "CDM RTN" if refinement.pc_method == "cdm_rtn" else "TLE RTN"
    line = (
        f"ESCALATION: {satellite.name} (NORAD {satellite.norad_id}) vs "
        f"{alert.debris_name} (NORAD {alert.debris_norad_id}): "
        f"screening Pc={_format_pc(refinement.pc_screening)} → "
        f"refined Pc={_format_pc(refinement.pc_refined)} ({method_label}) / "
        f"TCA={alert.tca.isoformat()}"
    )

    fmt = _webhook_format()
    if fmt in ("slack", "slack_bot"):
        payload = {"text": f"*CAS Pc Escalation*\n{line}"}
    elif fmt == "smtp":
        payload = {
            "subject": f"CAS Pc Escalation — {satellite.name}",
            "text": line,
        }
    elif fmt == "pagerduty":
        payload = _build_pagerduty_enqueue(
            f"CAS Pc Escalation — {satellite.name} vs {alert.debris_name}",
            "critical",
            {
                "escalation": True,
                "alert_id": str(alert.id),
                "satellite": {"name": satellite.name, "norad_id": satellite.norad_id},
                "debris": {"name": alert.debris_name, "norad_id": alert.debris_norad_id},
                "pc_screening": refinement.pc_screening,
                "pc_refined": refinement.pc_refined,
                "pc_method": refinement.pc_method,
                "trigger_source": refinement.trigger_source,
                "tca": alert.tca.isoformat(),
                "message": line,
            },
            dedup_key=pagerduty_dedup_key(alert.id),
        )
    else:
        payload = {
            "source": "cas",
            "escalation": True,
            "alert_id": str(alert.id),
            "satellite": {"name": satellite.name, "norad_id": satellite.norad_id},
            "debris": {"name": alert.debris_name, "norad_id": alert.debris_norad_id},
            "pc_screening": refinement.pc_screening,
            "pc_refined": refinement.pc_refined,
            "pc_method": refinement.pc_method,
            "trigger_source": refinement.trigger_source,
            "tca": alert.tca.isoformat(),
            "message": line,
        }

    return _post_payload(payload, 1)


def notify_mitigation_best(alert, best_preview) -> WebhookResult:
    """POST best mitigation preview from auto sweep (Phase 10F)."""
    from backend.app.db.models import AlertMitigationPreview, ConjunctionAlert

    if not _is_delivery_configured():
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message=_delivery_not_configured_message(),
        )
    if not isinstance(alert, ConjunctionAlert) or not isinstance(
        best_preview, AlertMitigationPreview
    ):
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message="通知対象が不正です。",
        )

    satellite = alert.satellite
    if satellite is None:
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message="衛星情報がありません。",
        )

    line = (
        f"COLA BEST: {satellite.name} (NORAD {satellite.norad_id}) vs "
        f"{alert.debris_name} (NORAD {alert.debris_norad_id}): "
        f"Δv {best_preview.delta_v_ms} m/s ({best_preview.direction}), "
        f"miss {best_preview.before_miss_distance_km:.3f}→"
        f"{best_preview.after_miss_distance_km:.3f} km / "
        f"TCA={alert.tca.isoformat()}"
    )

    fmt = _webhook_format()
    if fmt in ("slack", "slack_bot"):
        payload = {"text": f"*CAS Mitigation Best*\n{line}"}
    elif fmt == "smtp":
        payload = {
            "subject": f"CAS Mitigation Best — {satellite.name}",
            "text": line,
        }
    elif fmt == "pagerduty":
        payload = _build_pagerduty_enqueue(
            f"CAS Mitigation Best — {satellite.name} vs {alert.debris_name}",
            "warning",
            {
                "mitigation_best": True,
                "alert_id": str(alert.id),
                "satellite": {"name": satellite.name, "norad_id": satellite.norad_id},
                "debris": {"name": alert.debris_name, "norad_id": alert.debris_norad_id},
                "preview_id": str(best_preview.id),
                "direction": best_preview.direction,
                "delta_v_ms": best_preview.delta_v_ms,
                "before_miss_distance_km": best_preview.before_miss_distance_km,
                "after_miss_distance_km": best_preview.after_miss_distance_km,
                "trigger_source": best_preview.trigger_source,
                "tca": alert.tca.isoformat(),
                "message": line,
            },
            dedup_key=pagerduty_dedup_key(alert.id),
        )
    else:
        payload = {
            "source": "cas",
            "mitigation_best": True,
            "alert_id": str(alert.id),
            "satellite": {"name": satellite.name, "norad_id": satellite.norad_id},
            "debris": {"name": alert.debris_name, "norad_id": alert.debris_norad_id},
            "preview_id": str(best_preview.id),
            "direction": best_preview.direction,
            "delta_v_ms": best_preview.delta_v_ms,
            "before_miss_distance_km": best_preview.before_miss_distance_km,
            "after_miss_distance_km": best_preview.after_miss_distance_km,
            "trigger_source": best_preview.trigger_source,
            "tca": alert.tca.isoformat(),
            "message": line,
        }

    return _post_payload(payload, 1)


def notify_mitigation_plan_auto(alert, preview) -> WebhookResult:
    """POST auto mitigation plan transition (Phase 10G)."""
    from backend.app.db.models import AlertMitigationPreview, ConjunctionAlert

    if not _is_delivery_configured():
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message=_delivery_not_configured_message(),
        )
    if not isinstance(alert, ConjunctionAlert) or not isinstance(
        preview, AlertMitigationPreview
    ):
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message="通知対象が不正です。",
        )

    satellite = alert.satellite
    if satellite is None:
        return WebhookResult(
            sent=False,
            alert_count=0,
            degraded=False,
            message="衛星情報がありません。",
        )

    line = (
        f"COLA AUTO PLAN: {satellite.name} (NORAD {satellite.norad_id}) vs "
        f"{alert.debris_name} (NORAD {alert.debris_norad_id}): "
        f"status→{alert.status}, Δv {preview.delta_v_ms} m/s ({preview.direction}), "
        f"miss {preview.before_miss_distance_km:.3f}→"
        f"{preview.after_miss_distance_km:.3f} km / "
        f"TCA={alert.tca.isoformat()}"
    )

    fmt = _webhook_format()
    if fmt in ("slack", "slack_bot"):
        payload = {"text": f"*CAS Mitigation Plan Auto*\n{line}"}
    elif fmt == "smtp":
        payload = {
            "subject": f"CAS Mitigation Plan Auto — {satellite.name}",
            "text": line,
        }
    elif fmt == "pagerduty":
        payload = _build_pagerduty_enqueue(
            f"CAS Mitigation Plan Auto — {satellite.name} vs {alert.debris_name}",
            "warning",
            {
                "mitigation_plan_auto": True,
                "alert_id": str(alert.id),
                "status": alert.status,
                "satellite": {"name": satellite.name, "norad_id": satellite.norad_id},
                "debris": {"name": alert.debris_name, "norad_id": alert.debris_norad_id},
                "preview_id": str(preview.id),
                "direction": preview.direction,
                "delta_v_ms": preview.delta_v_ms,
                "before_miss_distance_km": preview.before_miss_distance_km,
                "after_miss_distance_km": preview.after_miss_distance_km,
                "trigger_source": preview.trigger_source,
                "tca": alert.tca.isoformat(),
                "message": line,
            },
            dedup_key=pagerduty_dedup_key(alert.id),
        )
    else:
        payload = {
            "source": "cas",
            "mitigation_plan_auto": True,
            "alert_id": str(alert.id),
            "status": alert.status,
            "satellite": {"name": satellite.name, "norad_id": satellite.norad_id},
            "debris": {"name": alert.debris_name, "norad_id": alert.debris_norad_id},
            "preview_id": str(preview.id),
            "direction": preview.direction,
            "delta_v_ms": preview.delta_v_ms,
            "before_miss_distance_km": preview.before_miss_distance_km,
            "after_miss_distance_km": preview.after_miss_distance_km,
            "trigger_source": preview.trigger_source,
            "tca": alert.tca.isoformat(),
            "message": line,
        }

    return _post_payload(payload, 1)


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
    elif fmt == "smtp":
        payload = {"subject": "CAS webhook test", "text": "CAS webhook test ping"}
    elif fmt == "pagerduty":
        payload = _build_pagerduty_enqueue(
            "CAS webhook test ping",
            "info",
            {"test": True, "message": "CAS webhook test ping"},
            dedup_key="cas-webhook-test",
        )
    else:
        payload = {
            "source": "cas",
            "test": True,
            "message": "CAS webhook test ping",
        }
    return _post_payload(payload, 0)
