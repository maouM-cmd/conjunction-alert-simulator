"""PagerDuty inbound webhook sync (Phase 10P)."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from backend.app.services import alert_service, audit_service
from backend.app.services.webhook_notifier import pagerduty_dedup_key

logger = logging.getLogger(__name__)

DEDUP_PREFIX = "cas-alert-"
INBOUND_COMMENT = "PagerDuty inbound sync"

ACK_EVENT_TYPES = frozenset({"incident.acknowledged"})
RESOLVE_EVENT_TYPES = frozenset({"incident.resolved"})


class PagerDutyInboundError(Exception):
    pass


class SignatureError(PagerDutyInboundError):
    pass


@dataclass
class PagerDutyInboundResult:
    processed: bool
    alert_id: uuid.UUID | None = None
    status: str | None = None
    noop: bool = False
    message: str = ""


def pagerduty_inbound_enabled() -> bool:
    raw = os.environ.get("PAGERDUTY_INBOUND_SYNC_ENABLED", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def pagerduty_webhook_signing_secret() -> str | None:
    secret = os.environ.get("PAGERDUTY_WEBHOOK_SIGNING_SECRET", "").strip()
    return secret or None


def parse_dedup_alert_id(dedup_key: str | None) -> uuid.UUID | None:
    if not dedup_key or not dedup_key.startswith(DEDUP_PREFIX):
        return None
    try:
        return uuid.UUID(dedup_key[len(DEDUP_PREFIX) :])
    except ValueError:
        return None


def extract_dedup_key(payload: dict[str, Any]) -> str | None:
    event = payload.get("event") or {}
    data = event.get("data") or {}
    for key in ("dedup_key", "incident_key"):
        value = data.get(key)
        if value:
            return str(value)
    return None


def verify_pagerduty_signature(headers: dict[str, str], body: bytes) -> bool:
    secret = pagerduty_webhook_signing_secret()
    if not secret:
        return False
    signature_header = ""
    for name, value in headers.items():
        if name.lower() == "x-pagerduty-signature":
            signature_header = value
            break
    if not signature_header:
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    for part in signature_header.split(","):
        sig = part.strip()
        if sig.startswith("v1="):
            sig = sig[3:]
        if hmac.compare_digest(sig, expected):
            return True
    return False


def _target_status_for_ack(current_status: str) -> str | None:
    if current_status == "open":
        return "acknowledged"
    if current_status in ("acknowledged", "mitigation_planned", "closed", "false_positive"):
        return None
    return None


def _resolve_status_chain(current_status: str) -> list[str]:
    if current_status in ("closed", "false_positive"):
        return []
    if current_status == "open":
        return ["acknowledged", "closed"]
    if current_status in ("acknowledged", "mitigation_planned"):
        return ["closed"]
    return []


def handle_pagerduty_event(db: Session, payload: dict[str, Any]) -> PagerDutyInboundResult:
    event = payload.get("event") or {}
    event_type = str(event.get("event_type") or "")
    dedup_key = extract_dedup_key(payload)
    alert_id = parse_dedup_alert_id(dedup_key)
    if alert_id is None:
        logger.info("PagerDuty inbound: unknown or missing dedup_key=%s", dedup_key)
        return PagerDutyInboundResult(
            processed=False,
            message="dedup_key が CAS 形式ではありません。",
        )

    try:
        alert = alert_service.get_alert(db, alert_id)
    except alert_service.NotFoundError:
        logger.info("PagerDuty inbound: alert not found id=%s", alert_id)
        return PagerDutyInboundResult(
            processed=False,
            alert_id=alert_id,
            message="アラートが見つかりません。",
        )

    if event_type in ACK_EVENT_TYPES:
        target = _target_status_for_ack(alert.status)
        if target is None:
            return PagerDutyInboundResult(
                processed=True,
                alert_id=alert_id,
                status=alert.status,
                noop=True,
                message="既に acknowledge 済みです。",
            )
        chain = [target]
    elif event_type in RESOLVE_EVENT_TYPES:
        chain = _resolve_status_chain(alert.status)
        if not chain:
            return PagerDutyInboundResult(
                processed=True,
                alert_id=alert_id,
                status=alert.status,
                noop=True,
                message="既に resolve 済みです。",
            )
    else:
        logger.info("PagerDuty inbound: ignored event_type=%s", event_type)
        return PagerDutyInboundResult(
            processed=False,
            alert_id=alert_id,
            status=alert.status,
            message=f"未対応の event_type: {event_type}",
        )

    from_status = alert.status
    for new_status in chain:
        try:
            alert = alert_service.transition_alert(
                db,
                alert_id,
                new_status=new_status,
                comment=INBOUND_COMMENT,
                skip_pagerduty_outbound=True,
            )
        except alert_service.ValidationError as exc:
            logger.warning(
                "PagerDuty inbound: transition blocked %s -> %s: %s",
                alert.status,
                new_status,
                exc,
            )
            return PagerDutyInboundResult(
                processed=False,
                alert_id=alert_id,
                status=alert.status,
                message=str(exc),
            )

    audit_service.log_audit(
        db,
        fleet_id=alert.fleet_id,
        action="alert.pagerduty_inbound",
        resource_type="alert",
        resource_id=alert.id,
        detail={
            "event_type": event_type,
            "dedup_key": dedup_key or pagerduty_dedup_key(alert_id),
            "from_status": from_status,
            "to_status": alert.status,
        },
    )
    db.commit()

    return PagerDutyInboundResult(
        processed=True,
        alert_id=alert_id,
        status=alert.status,
        message="同期しました。",
    )
