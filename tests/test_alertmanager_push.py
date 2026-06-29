"""Tests for Alertmanager push on fleet breach (Phase 10S)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import Base
from backend.app.db.session import get_engine, reset_engine_for_tests
from backend.app.services import alertmanager_push_service, fleet_alert_metrics_service
from backend.app.services.alert_service import ingest_screening_results
from backend.app.services.fleet_service import add_satellite, create_fleet
from tests.test_alerts_ops import _make_event, _make_result


@pytest.fixture
def ops_client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    from backend.app.main import app

    with TestClient(app) as client:
        yield client
    reset_engine_for_tests()


@pytest.fixture(autouse=True)
def reset_breach_state():
    alertmanager_push_service.reset_breach_state_for_tests()
    yield
    alertmanager_push_service.reset_breach_state_for_tests()


def _seed_high_open_alert(db):
    from pathlib import Path

    demo_sat = (Path(__file__).resolve().parents[1] / "samples" / "demo-satellite.tle").read_text(
        encoding="utf-8"
    ).strip()
    fleet = create_fleet(db, name="AM Push Fleet")
    sat = add_satellite(db, fleet.id, name=None, norad_id=None, tle=demo_sat)
    ingest_screening_results(
        db,
        run_id=uuid.uuid4(),
        fleet_id=fleet.id,
        results=[_make_result(events=[_make_event(risk="high")])],
        satellite_by_norad={sat.norad_id: sat.id},
    )
    return fleet


@patch("backend.app.services.alertmanager_push_service.httpx.Client")
def test_sync_breaches_fires_on_high_risk(mock_client_cls, monkeypatch):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_PUSH_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    monkeypatch.setenv("FLEET_ALERT_HIGH_RISK_THRESHOLD", "1")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    from backend.app.db.session import get_session_factory

    factory = get_session_factory()
    assert factory is not None
    db = factory()
    try:
        fleet = _seed_high_open_alert(db)
        counts = fleet_alert_metrics_service.collect_fleet_alert_counts(db)
        risk_counts = fleet_alert_metrics_service.collect_fleet_risk_counts(db)
        fleet_names = {fleet.id: fleet.name}
        alertmanager_push_service.sync_breaches(counts, risk_counts, fleet_names)
    finally:
        db.close()
    reset_engine_for_tests()

    assert mock_client.post.call_count == 1
    payload = mock_client.post.call_args.kwargs["json"]
    alertnames = {item["labels"]["alertname"] for item in payload}
    assert alertmanager_push_service.ALERT_HIGH_RISK in alertnames


@patch("backend.app.services.alertmanager_push_service.httpx.Client")
def test_sync_breaches_resolves_when_cleared(mock_client_cls, monkeypatch):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_PUSH_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    monkeypatch.setenv("FLEET_ALERT_HIGH_RISK_THRESHOLD", "1")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    fleet_id = uuid.uuid4()
    counts = {fleet_id: {"open": 1, "escalated": 0, "acknowledged": 0, "mitigation_planned": 0, "closed": 0, "false_positive": 0}}
    risk_counts = {fleet_id: {"high": {"open": 1}, "medium": {"open": 0}, "low": {"open": 0}}}
    fleet_names = {fleet_id: "Test Fleet"}

    alertmanager_push_service.sync_breaches(counts, risk_counts, fleet_names)
    cleared_counts = {fleet_id: {**counts[fleet_id], "open": 0}}
    cleared_risk = {fleet_id: {"high": {"open": 0}, "medium": {"open": 0}, "low": {"open": 0}}}
    alertmanager_push_service.sync_breaches(cleared_counts, cleared_risk, fleet_names)

    assert mock_client.post.call_count == 2
    resolve_payload = mock_client.post.call_args_list[1].kwargs["json"]
    assert any("endsAt" in item for item in resolve_payload)


@patch("backend.app.services.alertmanager_push_service.push_alerts")
def test_alertmanager_test_endpoint(mock_push, ops_client, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_PUSH_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")
    mock_push.return_value = alertmanager_push_service.PushResult(sent=True, message="ok")

    response = ops_client.post("/api/v1/ops/prometheus/alertmanager/test")
    assert response.status_code == 200
    assert response.json()["sent"] is True


def test_alertmanager_test_endpoint_disabled_returns_503(ops_client, monkeypatch):
    monkeypatch.delenv("ALERTMANAGER_PUSH_ENABLED", raising=False)
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")
    response = ops_client.post("/api/v1/ops/prometheus/alertmanager/test")
    assert response.status_code == 503
