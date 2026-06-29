"""Tests for API availability SLO (Phase 10H)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import Base, ScreeningRun, ScreeningSchedule
from backend.app.db.session import get_engine, reset_engine_for_tests
from backend.app.services import api_availability_service, fleet_service, screening_service


@pytest.fixture(autouse=True)
def reset_availability():
    api_availability_service.reset_availability_for_tests()
    yield
    api_availability_service.reset_availability_for_tests()


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


def test_compute_availability_all_success(monkeypatch):
    monkeypatch.setenv("SLA_API_TARGET_PERCENT", "99.9")
    for _ in range(100):
        api_availability_service.record_http_status(200)
    summary = api_availability_service.compute_api_availability()
    assert summary.availability_ratio == 1.0
    assert summary.slo_ok is True
    assert summary.request_count == 100
    assert summary.errors_5xx == 0


def test_compute_availability_5xx_breach(monkeypatch):
    monkeypatch.setenv("SLA_API_TARGET_PERCENT", "99.9")
    for _ in range(999):
        api_availability_service.record_http_status(200)
    for _ in range(2):
        api_availability_service.record_http_status(500)
    summary = api_availability_service.compute_api_availability()
    assert summary.request_count == 1001
    assert summary.errors_5xx == 2
    assert summary.availability_ratio is not None
    assert summary.availability_ratio < 0.999
    assert summary.slo_ok is False


def test_4xx_counts_as_success(monkeypatch):
    monkeypatch.setenv("SLA_API_TARGET_PERCENT", "99.9")
    for _ in range(50):
        api_availability_service.record_http_status(404)
    summary = api_availability_service.compute_api_availability()
    assert summary.availability_ratio == 1.0
    assert summary.slo_ok is True


def test_no_samples_returns_null_ratio(monkeypatch):
    monkeypatch.setenv("SLA_API_TARGET_PERCENT", "99.9")
    summary = api_availability_service.compute_api_availability()
    assert summary.availability_ratio is None
    assert summary.slo_ok is True
    assert summary.request_count == 0


def test_env_target_percent_respected(monkeypatch):
    monkeypatch.setenv("SLA_API_TARGET_PERCENT", "95")
    for _ in range(96):
        api_availability_service.record_http_status(200)
    for _ in range(4):
        api_availability_service.record_http_status(503)
    summary = api_availability_service.compute_api_availability()
    assert summary.slo_target_percent == 95.0
    assert summary.availability_ratio == 0.96
    assert summary.slo_ok is True


def test_metrics_path_not_recorded_in_tracker(ops_client):
    api_availability_service.reset_availability_for_tests()
    ops_client.get("/metrics")
    summary = api_availability_service.compute_api_availability()
    assert summary.request_count == 0


def test_ops_sla_includes_api_fields(ops_client, monkeypatch):
    monkeypatch.setenv("SLA_API_TARGET_PERCENT", "99.9")
    fleet = ops_client.post("/api/v1/fleets", json={"name": "SLO Fleet"}).json()
    for _ in range(10):
        ops_client.get("/health")

    response = ops_client.get(f"/api/v1/ops/sla?fleet_id={fleet['id']}")
    assert response.status_code == 200
    body = response.json()
    assert "api_availability_ratio" in body
    assert "api_availability_percent" in body
    assert body["api_slo_target_percent"] == 99.9
    assert "api_slo_ok" in body
    assert body["api_request_count"] >= 10
    assert body["api_availability_ratio"] == 1.0


def test_prometheus_exports_api_slo_gauges(ops_client, monkeypatch):
    monkeypatch.setenv("SLA_API_TARGET_PERCENT", "99.9")
    ops_client.get("/health")
    body = ops_client.get("/metrics").text
    assert "cas_api_availability_ratio" in body
    assert "cas_api_slo_ok" in body


def _seed_fleet_with_schedule(db) -> uuid.UUID:
    fleet = fleet_service.create_fleet(db, name="API SLO Fleet")
    screening_service.create_schedule(
        db,
        fleet_id=fleet.id,
        name="Daily",
        cron_expression="0 0 * * *",
    )
    return fleet.id


def test_ops_sla_with_screening_and_api_slo(ops_client, monkeypatch):
    from backend.app.db.session import get_session_factory

    monkeypatch.setenv("SLA_API_TARGET_PERCENT", "99.9")
    fleet = ops_client.post("/api/v1/fleets", json={"name": "Combined SLA"}).json()
    fleet_id = uuid.UUID(fleet["id"])

    db = get_session_factory()()
    try:
        schedule = (
            db.query(ScreeningSchedule)
            .filter(ScreeningSchedule.fleet_id == fleet_id)
            .first()
        )
        if schedule is None:
            _seed_fleet_with_schedule(db)
            schedule = (
                db.query(ScreeningSchedule)
                .filter(ScreeningSchedule.fleet_id == fleet_id)
                .first()
            )
        db.add(
            ScreeningRun(
                fleet_id=fleet_id,
                schedule_id=schedule.id if schedule else None,
                status="completed",
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
                satellite_count=1,
                event_count=0,
            )
        )
        db.commit()
    finally:
        db.close()

    ops_client.get("/health")
    response = ops_client.get(f"/api/v1/ops/sla?fleet_id={fleet['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["screening_sla_ok"] is True
    assert body["api_slo_ok"] is True
