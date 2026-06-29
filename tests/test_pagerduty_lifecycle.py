"""Tests for PagerDuty acknowledge/resolve lifecycle (Phase 10O)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from backend.app.db.models import Base
from backend.app.db.session import get_engine, reset_engine_for_tests
from backend.app.services.webhook_notifier import (
    _build_pagerduty_enqueue,
    notify_new_alerts,
    pagerduty_dedup_key,
    pagerduty_lifecycle_enabled,
)

PAGERDUTY_ENV = {
    "ALERT_WEBHOOK_FORMAT": "pagerduty",
    "PAGERDUTY_ROUTING_KEY": "test-routing-key",
}

PAGERDUTY_LIFECYCLE_ENV = {
    **PAGERDUTY_ENV,
    "PAGERDUTY_LIFECYCLE_ENABLED": "true",
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


def test_pagerduty_lifecycle_disabled_by_default(monkeypatch):
    monkeypatch.delenv("PAGERDUTY_LIFECYCLE_ENABLED", raising=False)
    assert pagerduty_lifecycle_enabled() is False


def test_pagerduty_dedup_key_format():
    alert_id = uuid.uuid4()
    assert pagerduty_dedup_key(alert_id) == f"cas-alert-{alert_id}"


def test_build_pagerduty_enqueue_acknowledge_and_resolve():
    with patch.dict(os.environ, PAGERDUTY_ENV, clear=False):
        alert_id = uuid.uuid4()
        dedup = pagerduty_dedup_key(alert_id)
        ack = _build_pagerduty_enqueue(
            "CAS alert acknowledge",
            "info",
            {"alert_id": str(alert_id)},
            dedup_key=dedup,
            event_action="acknowledge",
        )
        resolve = _build_pagerduty_enqueue(
            "CAS alert resolve",
            "info",
            {"alert_id": str(alert_id)},
            dedup_key=dedup,
            event_action="resolve",
        )
    assert ack["event_action"] == "acknowledge"
    assert resolve["event_action"] == "resolve"
    assert ack["dedup_key"] == dedup
    assert resolve["dedup_key"] == dedup


@patch("backend.app.services.webhook_notifier.httpx.Client")
def test_notify_new_alerts_pagerduty_per_alert_triggers(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 202
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    alert_cls = type("ConjunctionAlert", (object,), {})
    alert1_id = uuid.uuid4()
    alert2_id = uuid.uuid4()
    alerts = []
    for alert_id, debris in ((alert1_id, "DEB1"), (alert2_id, "DEB2")):
        alert = alert_cls()
        alert.id = alert_id
        alert.debris_name = debris
        alert.debris_norad_id = 1000
        alert.tca = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        alert.miss_distance_km = 1.0
        alert.risk_level = "high"
        alert.pc = 1e-4
        alert.satellite = type("Sat", (object,), {"name": "SAT", "norad_id": 25544})()
        alert.satellite_id = uuid.uuid4()
        alerts.append(alert)

    with (
        patch.dict(os.environ, PAGERDUTY_LIFECYCLE_ENV, clear=False),
        patch("backend.app.db.models.ConjunctionAlert", alert_cls),
    ):
        result = notify_new_alerts(alerts)
        assert result.sent is True
        assert result.alert_count == 2
        assert mock_client.post.call_count == 2
        keys = {
            call.kwargs["json"]["dedup_key"] for call in mock_client.post.call_args_list
        }
        assert keys == {pagerduty_dedup_key(alert1_id), pagerduty_dedup_key(alert2_id)}


@patch("backend.app.services.webhook_notifier.httpx.Client")
def test_notify_new_alerts_pagerduty_lifecycle_off_batch(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 202
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    alert_cls = type("ConjunctionAlert", (object,), {})
    alert_id = uuid.uuid4()
    alert = alert_cls()
    alert.id = alert_id
    alert.debris_name = "DEB1"
    alert.debris_norad_id = 1000
    alert.tca = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
    alert.miss_distance_km = 1.0
    alert.risk_level = "high"
    alert.pc = 1e-4
    alert.satellite = type("Sat", (object,), {"name": "SAT", "norad_id": 25544})()
    alert.satellite_id = uuid.uuid4()

    with (
        patch.dict(os.environ, {**PAGERDUTY_ENV, "PAGERDUTY_LIFECYCLE_ENABLED": "false"}, clear=False),
        patch("backend.app.db.models.ConjunctionAlert", alert_cls),
    ):
        result = notify_new_alerts([alert])
        assert result.sent is True
        assert result.alert_count == 1
        assert mock_client.post.call_count == 1
        body = mock_client.post.call_args.kwargs["json"]
        assert body["event_action"] == "trigger"
        assert "dedup_key" not in body


@patch("backend.app.services.webhook_notifier.httpx.Client")
def test_transition_alert_sends_acknowledge(mock_client_cls, db_session):
    from backend.app.services import fleet_service
    from backend.app.services.alert_service import ingest_screening_results, transition_alert as svc_transition
    from tests.test_alerts_ops import _make_result

    mock_response = MagicMock()
    mock_response.status_code = 202
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    db = db_session
    fleet = fleet_service.create_fleet(db, name="PD Lifecycle")
    from pathlib import Path

    demo_sat = (Path(__file__).resolve().parents[1] / "samples" / "demo-satellite.tle").read_text(
        encoding="utf-8"
    ).strip()
    sat = fleet_service.add_satellite(db, fleet.id, name=None, norad_id=None, tle=demo_sat)
    opens = ingest_screening_results(
        db,
        run_id=uuid.uuid4(),
        fleet_id=fleet.id,
        results=[_make_result()],
        satellite_by_norad={sat.norad_id: sat.id},
    )
    alert_id = opens[0].id

    with patch.dict(os.environ, PAGERDUTY_LIFECYCLE_ENV, clear=False):
        svc_transition(db, alert_id, new_status="acknowledged", comment="seen")
        body = mock_client.post.call_args.kwargs["json"]
        assert body["event_action"] == "acknowledge"
        assert body["dedup_key"] == pagerduty_dedup_key(alert_id)


@patch("backend.app.services.webhook_notifier.httpx.Client")
def test_transition_alert_sends_resolve(mock_client_cls, db_session):
    from backend.app.services import fleet_service
    from backend.app.services.alert_service import ingest_screening_results, transition_alert as svc_transition
    from tests.test_alerts_ops import _make_result

    mock_response = MagicMock()
    mock_response.status_code = 202
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    db = db_session
    fleet = fleet_service.create_fleet(db, name="PD Resolve")
    from pathlib import Path

    demo_sat = (Path(__file__).resolve().parents[1] / "samples" / "demo-satellite.tle").read_text(
        encoding="utf-8"
    ).strip()
    sat = fleet_service.add_satellite(db, fleet.id, name=None, norad_id=None, tle=demo_sat)
    opens = ingest_screening_results(
        db,
        run_id=uuid.uuid4(),
        fleet_id=fleet.id,
        results=[_make_result()],
        satellite_by_norad={sat.norad_id: sat.id},
    )
    alert_id = opens[0].id

    with patch.dict(os.environ, PAGERDUTY_LIFECYCLE_ENV, clear=False):
        svc_transition(db, alert_id, new_status="acknowledged")
        svc_transition(db, alert_id, new_status="closed", comment="done")
        resolve_call = mock_client.post.call_args_list[-1]
        body = resolve_call.kwargs["json"]
        assert body["event_action"] == "resolve"
        assert body["dedup_key"] == pagerduty_dedup_key(alert_id)
