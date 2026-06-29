"""Alertmanager silences API (Phase 10T)."""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from backend.app.services.alertmanager_push_service import alertmanager_url

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SEC = 10.0
VALID_ALERTNAMES = frozenset(
    {"CASFleetOpenAlertsHigh", "CASFleetHighRiskOpenAlerts"}
)
TRIAGE_AUTO_SILENCE_STATUSES = frozenset({"acknowledged", "false_positive"})


@dataclass(frozen=True)
class SilenceResult:
    ok: bool
    message: str
    silence_id: str | None = None


@dataclass(frozen=True)
class SilenceItem:
    silence_id: str
    fleet_id: str | None
    alertname: str | None
    starts_at: datetime | None
    ends_at: datetime | None
    comment: str | None


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def alertmanager_silences_enabled() -> bool:
    return _env_bool("ALERTMANAGER_SILENCES_ENABLED", default=False)


def alertmanager_silences_configured() -> bool:
    return alertmanager_silences_enabled() and bool(alertmanager_url())


def default_silence_hours() -> float:
    raw = os.environ.get("ALERTMANAGER_SILENCE_DEFAULT_HOURS", "").strip()
    if not raw:
        return 4.0
    try:
        return max(float(raw), 0.25)
    except ValueError:
        return 4.0


def auto_silence_on_triage_enabled() -> bool:
    return _env_bool("ALERTMANAGER_AUTO_SILENCE_ON_TRIAGE_ENABLED", default=False)


def auto_silence_hours() -> float:
    raw = os.environ.get("ALERTMANAGER_AUTO_SILENCE_HOURS", "").strip()
    if not raw:
        return default_silence_hours()
    try:
        return max(float(raw), 0.25)
    except ValueError:
        return default_silence_hours()


def _basic_auth() -> tuple[str, str] | None:
    user = os.environ.get("ALERTMANAGER_BASIC_AUTH_USER", "").strip()
    password = os.environ.get("ALERTMANAGER_BASIC_AUTH_PASSWORD", "").strip()
    if user and password:
        return user, password
    return None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_am_time(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _build_matchers(fleet_id: uuid.UUID, alertname: str | None) -> list[dict[str, Any]]:
    matchers = [
        {"name": "fleet_id", "value": str(fleet_id), "isRegex": False},
    ]
    if alertname:
        matchers.append({"name": "alertname", "value": alertname, "isRegex": False})
    return matchers


def _silence_payload_from_am(data: dict[str, Any]) -> SilenceItem:
    fleet_id: str | None = None
    alertname: str | None = None
    for matcher in data.get("matchers", []):
        name = matcher.get("name")
        value = matcher.get("value")
        if name == "fleet_id":
            fleet_id = value
        elif name == "alertname":
            alertname = value
    status = data.get("status", {}) or {}
    return SilenceItem(
        silence_id=str(data.get("id", "")),
        fleet_id=fleet_id,
        alertname=alertname,
        starts_at=_parse_am_time(status.get("startsAt")),
        ends_at=_parse_am_time(status.get("endsAt")),
        comment=data.get("comment"),
    )


def create_fleet_silence(
    fleet_id: uuid.UUID,
    *,
    alertname: str | None = None,
    duration_hours: float | None = None,
    comment: str | None = None,
) -> SilenceResult:
    if not alertmanager_silences_configured():
        return SilenceResult(ok=False, message="Alertmanager silences は無効です。")

    if alertname is not None and alertname not in VALID_ALERTNAMES:
        return SilenceResult(ok=False, message=f"未対応の alertname です: {alertname}")

    url = alertmanager_url()
    assert url is not None
    hours = duration_hours if duration_hours is not None else default_silence_hours()
    starts_at = _utcnow()
    ends_at = starts_at + timedelta(hours=hours)
    payload = {
        "matchers": _build_matchers(fleet_id, alertname),
        "startsAt": starts_at.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "endsAt": ends_at.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "createdBy": "conjunction-alert-simulator",
        "comment": comment or f"CAS fleet silence ({fleet_id})",
    }
    endpoint = f"{url}/api/v2/silences"
    auth = _basic_auth()
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SEC) as client:
            response = client.post(endpoint, json=payload, auth=auth)
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        logger.warning("Alertmanager silence create failed: %s", exc)
        return SilenceResult(ok=False, message=f"silence 作成失敗: {exc}")

    silence_id = str(body.get("silenceID", ""))
    return SilenceResult(
        ok=True,
        message="silence を作成しました。",
        silence_id=silence_id or None,
    )


def list_silences(fleet_id: uuid.UUID | None = None) -> tuple[list[SilenceItem], str | None]:
    if not alertmanager_silences_configured():
        return [], "Alertmanager silences は無効です。"

    url = alertmanager_url()
    assert url is not None
    endpoint = f"{url}/api/v2/silences"
    auth = _basic_auth()
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SEC) as client:
            response = client.get(
                endpoint,
                params={"filter": "active=true"},
                auth=auth,
            )
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        logger.warning("Alertmanager silence list failed: %s", exc)
        return [], f"silence 一覧取得失敗: {exc}"

    items: list[SilenceItem] = []
    fleet_id_str = str(fleet_id) if fleet_id is not None else None
    for entry in body if isinstance(body, list) else []:
        item = _silence_payload_from_am(entry)
        if fleet_id_str is not None and item.fleet_id != fleet_id_str:
            continue
        items.append(item)
    return items, None


def get_silence(silence_id: str) -> SilenceItem | None:
    if not alertmanager_silences_configured():
        return None

    url = alertmanager_url()
    assert url is not None
    endpoint = f"{url}/api/v2/silence/{silence_id}"
    auth = _basic_auth()
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SEC) as client:
            response = client.get(endpoint, auth=auth)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        logger.warning("Alertmanager silence get failed: %s", exc)
        items, error = list_silences()
        if error:
            return None
        for item in items:
            if item.silence_id == silence_id:
                return item
        return None

    if isinstance(body, dict):
        return _silence_payload_from_am(body)
    return None


def delete_silence(silence_id: str) -> SilenceResult:
    if not alertmanager_silences_configured():
        return SilenceResult(ok=False, message="Alertmanager silences は無効です。")

    url = alertmanager_url()
    assert url is not None
    endpoint = f"{url}/api/v2/silence/{silence_id}"
    auth = _basic_auth()
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SEC) as client:
            response = client.delete(endpoint, auth=auth)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Alertmanager silence delete failed: %s", exc)
        return SilenceResult(ok=False, message=f"silence 削除失敗: {exc}")

    return SilenceResult(
        ok=True,
        message="silence を削除しました。",
        silence_id=silence_id,
    )


def maybe_auto_silence_on_triage(
    db,
    alert,
    *,
    old_status: str,
    new_status: str,
    api_key_id: uuid.UUID | None = None,
) -> SilenceResult | None:
    if not auto_silence_on_triage_enabled():
        return None
    if new_status not in TRIAGE_AUTO_SILENCE_STATUSES:
        return None
    if not alertmanager_silences_configured():
        return None

    result = create_fleet_silence(
        alert.fleet_id,
        duration_hours=auto_silence_hours(),
        comment=f"Auto silence after triage ({old_status} -> {new_status})",
    )
    if result.ok and result.silence_id:
        from backend.app.services import audit_service

        audit_service.log_audit(
            db,
            fleet_id=alert.fleet_id,
            action="alert.alertmanager_auto_silence",
            resource_type="alert",
            resource_id=alert.id,
            api_key_id=api_key_id,
            detail={
                "silence_id": result.silence_id,
                "from_status": old_status,
                "to_status": new_status,
            },
        )
        db.commit()
    elif not result.ok:
        logger.warning("Auto silence on triage failed for alert %s: %s", alert.id, result.message)
    return result
