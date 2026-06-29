"""Tests for per-fleet alert Prometheus metrics (Phase 10Q)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import Base
from backend.app.db.session import get_engine, reset_engine_for_tests
from backend.app.services import fleet_alert_metrics_service
from backend.app.services.alert_service import ingest_screening_results
from backend.app.services.fleet_service import add_satellite, create_fleet
from tests.test_alerts_ops import _make_event, _make_result
from tests.test_fleet_api_slo import _create_fleet_with_key


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


def test_fleet_alert_metrics_disabled_by_default(monkeypatch):
    monkeypatch.delenv("FLEET_ALERT_METRICS_ENABLED", raising=False)
    assert fleet_alert_metrics_service.fleet_alert_metrics_enabled() is False


def _seed_two_open_alerts(db):
    from pathlib import Path

    demo_sat = (Path(__file__).resolve().parents[1] / "samples" / "demo-satellite.tle").read_text(
        encoding="utf-8"
    ).strip()
    fleet = create_fleet(db, name="Alert Metrics Fleet")
    sat = add_satellite(db, fleet.id, name=None, norad_id=None, tle=demo_sat)
    tca1 = datetime.now(timezone.utc)
    ingest_screening_results(
        db,
        run_id=uuid.uuid4(),
        fleet_id=fleet.id,
        results=[_make_result(events=[_make_event(debris_norad=11111, tca=tca1)])],
        satellite_by_norad={sat.norad_id: sat.id},
    )
    ingest_screening_results(
        db,
        run_id=uuid.uuid4(),
        fleet_id=fleet.id,
        results=[_make_result(events=[_make_event(debris_norad=22222, tca=tca1 + timedelta(hours=30))])],
        satellite_by_norad={sat.norad_id: sat.id},
    )
    return fleet


def test_prometheus_exports_fleet_alert_metrics(ops_client, monkeypatch):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("FLEET_ALERT_OPEN_THRESHOLD", "1")
    from backend.app.db.session import get_session_factory

    factory = get_session_factory()
    assert factory is not None
    db_sess = factory()
    try:
        fleet = _seed_two_open_alerts(db_sess)
        fleet_id = str(fleet.id)
    finally:
        db_sess.close()

    response = ops_client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "cas_fleet_alerts_total" in body
    assert f'fleet_id="{fleet_id}"' in body
    assert 'status="open"' in body
    assert "cas_fleet_open_alerts_breach" in body


def test_fleet_alert_rules_endpoint_yaml(ops_client, monkeypatch):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    fleet_id, _fleet_key = _create_fleet_with_key(ops_client, monkeypatch, "Rules Fleet")

    from backend.app.db.session import get_session_factory
    from pathlib import Path

    factory = get_session_factory()
    assert factory is not None
    db_sess = factory()
    try:
        demo_sat = (Path(__file__).resolve().parents[1] / "samples" / "demo-satellite.tle").read_text(
            encoding="utf-8"
        ).strip()
        sat = add_satellite(db_sess, uuid.UUID(fleet_id), name=None, norad_id=None, tle=demo_sat)
        ingest_screening_results(
            db_sess,
            run_id=uuid.uuid4(),
            fleet_id=uuid.UUID(fleet_id),
            results=[_make_result()],
            satellite_by_norad={sat.norad_id: sat.id},
        )
    finally:
        db_sess.close()

    response = ops_client.get(
        f"/api/v1/ops/prometheus/fleet-alert-rules?fleet_id={fleet_id}",
        headers={"X-API-Key": "admin-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "yaml"
    assert data["fleet_id"] == fleet_id
    assert "cas_fleet_alerts_total" in data["content"]
    assert fleet_id in data["content"]
    assert "CASFleetOpenAlertsHigh" in data["content"]


def test_fleet_alert_rules_disabled_returns_503(ops_client, monkeypatch):
    monkeypatch.delenv("FLEET_ALERT_METRICS_ENABLED", raising=False)
    response = ops_client.get("/api/v1/ops/prometheus/fleet-alert-rules")
    assert response.status_code == 503


def test_fleet_scoped_key_cannot_access_other_fleet_rules(ops_client, monkeypatch):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    fleet_a, key_a = _create_fleet_with_key(ops_client, monkeypatch, "Fleet A Rules")
    fleet_b, _ = _create_fleet_with_key(ops_client, monkeypatch, "Fleet B Rules")

    response = ops_client.get(
        f"/api/v1/ops/prometheus/fleet-alert-rules?fleet_id={fleet_b}",
        headers={"X-API-Key": key_a},
    )
    assert response.status_code == 403


def test_render_fleet_alert_rules_json():
    rules = fleet_alert_metrics_service.render_fleet_alert_rules(
        uuid.uuid4(),
        "Test Fleet",
    )
    content = fleet_alert_metrics_service.render_fleet_alert_rules_json(rules)
    assert "cas-fleet-alerts" in content
    assert "CASFleetOpenAlertsHigh" in content
