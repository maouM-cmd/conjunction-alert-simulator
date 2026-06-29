"""Tests for PagerDuty inbound webhook sync (Phase 10P)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import Base
from backend.app.db.session import get_engine, reset_engine_for_tests
from backend.app.services.pagerduty_inbound_service import (
    handle_pagerduty_event,
    parse_dedup_alert_id,
    verify_pagerduty_signature,
)
from backend.app.services.webhook_notifier import pagerduty_dedup_key

WEBHOOK_SECRET = "test-webhook-secret"
INBOUND_ENV = {
    "PAGERDUTY_INBOUND_SYNC_ENABLED": "true",
    "PAGERDUTY_WEBHOOK_SIGNING_SECRET": WEBHOOK_SECRET,
    "ALERT_WEBHOOK_FORMAT": "pagerduty",
    "PAGERDUTY_ROUTING_KEY": "test-routing-key",
    "PAGERDUTY_LIFECYCLE_ENABLED": "true",
}


def _sign_body(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"v1={digest}"


def _payload(event_type: str, alert_id: uuid.UUID) -> dict:
    return {
        "event": {
            "event_type": event_type,
            "data": {
                "dedup_key": pagerduty_dedup_key(alert_id),
            },
        }
    }


@pytest.fixture
def db_session(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    reset_engine_for_tests()
    engine = get_engine()
    assert engine is not None
    Base.metadata.create_all(engine)
    from backend.app.db.session import get_session_factory

    factory = get_session_factory()
    assert factory is not None
    db = factory()
    try:
        yield db
    finally:
        db.close()
        reset_engine_for_tests()


@pytest.fixture
def inbound_client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    for key, value in INBOUND_ENV.items():
        monkeypatch.setenv(key, value)
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    from backend.app.main import app

    with TestClient(app) as client:
        yield client
    reset_engine_for_tests()


def _seed_open_alert(db):
    from backend.app.services import fleet_service
    from backend.app.services.alert_service import ingest_screening_results
    from pathlib import Path
    from tests.test_alerts_ops import _make_result

    demo_sat = (Path(__file__).resolve().parents[1] / "samples" / "demo-satellite.tle").read_text(
        encoding="utf-8"
    ).strip()
    fleet = fleet_service.create_fleet(db, name="PD Inbound Fleet")
    sat = fleet_service.add_satellite(db, fleet.id, name=None, norad_id=None, tle=demo_sat)
    opens = ingest_screening_results(
        db,
        run_id=uuid.uuid4(),
        fleet_id=fleet.id,
        results=[_make_result()],
        satellite_by_norad={sat.norad_id: sat.id},
    )
    return opens[0]


def test_parse_dedup_alert_id_valid_and_invalid():
    alert_id = uuid.uuid4()
    assert parse_dedup_alert_id(pagerduty_dedup_key(alert_id)) == alert_id
    assert parse_dedup_alert_id("cas-escalation-foo") is None
    assert parse_dedup_alert_id(None) is None


def test_verify_pagerduty_signature_valid_and_invalid():
    body = b'{"event":{"event_type":"incident.acknowledged"}}'
    headers = {"X-PagerDuty-Signature": _sign_body(body)}
    with patch.dict(os.environ, {"PAGERDUTY_WEBHOOK_SIGNING_SECRET": WEBHOOK_SECRET}, clear=False):
        assert verify_pagerduty_signature(headers, body) is True
        assert verify_pagerduty_signature(headers, body + b"x") is False
        assert verify_pagerduty_signature({}, body) is False


@patch("backend.app.services.webhook_notifier.httpx.Client")
def test_inbound_acknowledged_updates_alert_no_outbound(mock_client_cls, inbound_client, db_session):
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client_cls.return_value = mock_client

    alert = _seed_open_alert(db_session)
    body = json.dumps(_payload("incident.acknowledged", alert.id)).encode("utf-8")
    response = inbound_client.post(
        "/api/v1/integrations/pagerduty/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-PagerDuty-Signature": _sign_body(body),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["processed"] is True
    assert data["status"] == "acknowledged"
    mock_client.post.assert_not_called()


@patch("backend.app.services.webhook_notifier.httpx.Client")
def test_inbound_resolved_from_acknowledged(mock_client_cls, inbound_client, db_session):
    from backend.app.services.alert_service import transition_alert as svc_transition

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client_cls.return_value = mock_client

    alert = _seed_open_alert(db_session)
    svc_transition(db_session, alert.id, new_status="acknowledged")
    mock_client.post.reset_mock()

    body = json.dumps(_payload("incident.resolved", alert.id)).encode("utf-8")
    response = inbound_client.post(
        "/api/v1/integrations/pagerduty/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-PagerDuty-Signature": _sign_body(body),
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "closed"
    mock_client.post.assert_not_called()


@patch("backend.app.services.webhook_notifier.httpx.Client")
def test_inbound_resolved_from_open_chains_ack_and_close(mock_client_cls, inbound_client, db_session):
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client_cls.return_value = mock_client

    alert = _seed_open_alert(db_session)
    body = json.dumps(_payload("incident.resolved", alert.id)).encode("utf-8")
    response = inbound_client.post(
        "/api/v1/integrations/pagerduty/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-PagerDuty-Signature": _sign_body(body),
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "closed"
    mock_client.post.assert_not_called()


def test_inbound_disabled_returns_503(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.delenv("PAGERDUTY_INBOUND_SYNC_ENABLED", raising=False)
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    from backend.app.main import app

    client = TestClient(app)
    body = b"{}"
    response = client.post(
        "/api/v1/integrations/pagerduty/webhook",
        content=body,
        headers={"X-PagerDuty-Signature": "v1=deadbeef"},
    )
    assert response.status_code == 503
    reset_engine_for_tests()


def test_inbound_invalid_signature_returns_401(inbound_client):
    body = json.dumps(_payload("incident.acknowledged", uuid.uuid4())).encode("utf-8")
    response = inbound_client.post(
        "/api/v1/integrations/pagerduty/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-PagerDuty-Signature": "v1=invalid",
        },
    )
    assert response.status_code == 401


def test_inbound_acknowledged_idempotent_noop(db_session):
    alert = _seed_open_alert(db_session)
    with patch.dict(os.environ, INBOUND_ENV, clear=False):
        first = handle_pagerduty_event(db_session, _payload("incident.acknowledged", alert.id))
        second = handle_pagerduty_event(db_session, _payload("incident.acknowledged", alert.id))
    assert first.processed is True
    assert first.status == "acknowledged"
    assert second.noop is True
    assert second.status == "acknowledged"
