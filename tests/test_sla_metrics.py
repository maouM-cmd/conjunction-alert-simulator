"""Tests for SLA metrics (Phase 10B)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import Base, ScreeningRun, ScreeningSchedule
from backend.app.db.session import get_engine, get_session_factory, reset_engine_for_tests
from backend.app.metrics_registry import cas_http_requests_total
from backend.app.services import fleet_service, screening_service, sla_service


@pytest.fixture
def db_session(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    reset_engine_for_tests()
    engine = get_engine()
    assert engine is not None
    Base.metadata.create_all(engine)
    factory = get_session_factory()
    assert factory is not None
    db = factory()
    try:
        yield db
    finally:
        db.close()
        reset_engine_for_tests()


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


@pytest.fixture
def hardened_client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.delenv("CAS_API_KEY_REQUIRED", raising=False)
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    from backend.app.main import app

    with TestClient(app) as client:
        yield client
    reset_engine_for_tests()


def _seed_fleet_with_schedule(db) -> tuple[uuid.UUID, uuid.UUID]:
    fleet = fleet_service.create_fleet(db, name="SLA Fleet")
    schedule = screening_service.create_schedule(
        db,
        fleet_id=fleet.id,
        name="Daily",
        cron_expression="0 0 * * *",
    )
    return fleet.id, schedule.id


def _add_completed_parent_run(
    db,
    *,
    fleet_id: uuid.UUID,
    schedule_id: uuid.UUID,
    finished_at: datetime,
) -> ScreeningRun:
    run = ScreeningRun(
        id=uuid.uuid4(),
        schedule_id=schedule_id,
        fleet_id=fleet_id,
        status="completed",
        started_at=finished_at - timedelta(minutes=5),
        finished_at=finished_at,
        satellite_count=1,
        event_count=0,
        degraded=False,
        computation_time_ms=100,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def test_compute_fleet_sla_ok_within_24h(db_session):
    db = db_session
    fleet_id, schedule_id = _seed_fleet_with_schedule(db)
    finished = datetime.now(timezone.utc) - timedelta(hours=2)
    _add_completed_parent_run(db, fleet_id=fleet_id, schedule_id=schedule_id, finished_at=finished)

    summary = sla_service.compute_fleet_sla(db, fleet_id)
    assert summary.has_active_schedule is True
    assert summary.screening_sla_ok is True
    assert summary.screening_lag_hours is not None
    assert summary.screening_lag_hours < 24.0


def test_compute_fleet_sla_overdue(db_session, monkeypatch):
    monkeypatch.setenv("SLA_SCREENING_MAX_LAG_HOURS", "24")
    db = db_session
    fleet_id, schedule_id = _seed_fleet_with_schedule(db)
    finished = datetime.now(timezone.utc) - timedelta(hours=30)
    _add_completed_parent_run(db, fleet_id=fleet_id, schedule_id=schedule_id, finished_at=finished)

    summary = sla_service.compute_fleet_sla(db, fleet_id)
    assert summary.screening_sla_ok is False
    assert summary.screening_lag_hours is not None
    assert summary.screening_lag_hours > 24.0


def test_fleet_without_schedule(db_session):
    db = db_session
    fleet = fleet_service.create_fleet(db, name="No Schedule")

    summary = sla_service.compute_fleet_sla(db, fleet.id)
    assert summary.has_active_schedule is False
    assert summary.screening_lag_seconds is None
    assert summary.screening_sla_ok is True


def test_schedule_without_completed_run_is_not_ok(db_session):
    db = db_session
    fleet_id, _schedule_id = _seed_fleet_with_schedule(db)

    summary = sla_service.compute_fleet_sla(db, fleet_id)
    assert summary.has_active_schedule is True
    assert summary.screening_lag_seconds is None
    assert summary.screening_sla_ok is False


def test_ops_sla_endpoint(ops_client):
    fleet = ops_client.post("/api/v1/fleets", json={"name": "Ops SLA"}).json()
    schedule_resp = ops_client.post(
        "/api/v1/screening/schedules",
        json={
            "fleet_id": fleet["id"],
            "name": "SLA",
            "cron_expression": "0 0 * * *",
        },
    )
    assert schedule_resp.status_code == 201

    response = ops_client.get(f"/api/v1/ops/sla?fleet_id={fleet['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["screening_sla_target_hours"] == 24.0
    assert len(body["items"]) == 1
    assert body["items"][0]["has_active_schedule"] is True
    assert body["overdue_count"] == 1


def test_metrics_includes_sla_series(ops_client):
    fleet = ops_client.post("/api/v1/fleets", json={"name": "Metrics SLA"}).json()
    schedule_resp = ops_client.post(
        "/api/v1/screening/schedules",
        json={
            "fleet_id": fleet["id"],
            "name": "SLA",
            "cron_expression": "0 0 * * *",
        },
    )
    assert schedule_resp.status_code == 201

    response = ops_client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "cas_screening_lag_seconds" in body
    assert "cas_screening_overdue_fleets" in body
    assert "cas_http_requests_total" in body


def test_http_middleware_counts_requests(ops_client):
    before = cas_http_requests_total.labels(method="GET", status_class="2xx")._value.get()
    ops_client.get("/health")
    after = cas_http_requests_total.labels(method="GET", status_class="2xx")._value.get()
    assert after > before

    before_404 = cas_http_requests_total.labels(method="GET", status_class="4xx")._value.get()
    ops_client.get("/nonexistent-path-for-sla-test")
    after_404 = cas_http_requests_total.labels(method="GET", status_class="4xx")._value.get()
    assert after_404 > before_404


def test_wrong_fleet_api_key_returns_403(hardened_client, monkeypatch):
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")

    fleet_a = hardened_client.post(
        "/api/v1/fleets",
        json={"name": "Fleet A"},
        headers={"X-API-Key": "admin-secret"},
    ).json()
    fleet_b = hardened_client.post(
        "/api/v1/fleets",
        json={"name": "Fleet B"},
        headers={"X-API-Key": "admin-secret"},
    ).json()
    key_b = hardened_client.post(
        f"/api/v1/fleets/{fleet_b['id']}/api-keys",
        json={"name": "B key"},
        headers={"X-API-Key": "admin-secret"},
    ).json()["api_key"]

    response = hardened_client.get(
        f"/api/v1/ops/sla?fleet_id={fleet_a['id']}",
        headers={"X-API-Key": key_b},
    )
    assert response.status_code == 403
