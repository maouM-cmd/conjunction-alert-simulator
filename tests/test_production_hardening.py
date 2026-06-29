"""Tests for Phase 9E production hardening."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import Base
from backend.app.db.session import get_engine, get_session_factory, reset_engine_for_tests
from backend.app.services import api_key_service, audit_service, fleet_service, screening_service

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
DEMO_SAT = (SAMPLES / "demo-satellite.tle").read_text(encoding="utf-8").strip()


@pytest.fixture
def db_session(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.delenv("CAS_API_KEY_REQUIRED", raising=False)
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
def hardened_client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")
    monkeypatch.delenv("CAS_API_KEY_REQUIRED", raising=False)
    reset_engine_for_tests()
    from backend.app.tasks.celery_app import configure_celery_eager

    configure_celery_eager()
    engine = get_engine()
    assert engine is not None
    Base.metadata.create_all(engine)
    from backend.app.main import app

    with TestClient(app) as client:
        yield client
    reset_engine_for_tests()


def test_fleet_api_open_without_auth(hardened_client):
    response = hardened_client.post("/api/v1/fleets", json={"name": "Open Fleet"})
    assert response.status_code == 201


def test_api_key_auth_success(hardened_client, monkeypatch):
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")
    fleet = hardened_client.post(
        "/api/v1/fleets",
        json={"name": "Auth Fleet"},
        headers={"X-API-Key": "admin-secret"},
    ).json()
    created = hardened_client.post(
        f"/api/v1/fleets/{fleet['id']}/api-keys",
        json={"name": "ops"},
        headers={"X-API-Key": "admin-secret"},
    )
    assert created.status_code == 201
    plain = created.json()["api_key"]
    listing = hardened_client.get("/api/v1/fleets", headers={"X-API-Key": plain})
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_invalid_api_key_returns_401(hardened_client, monkeypatch):
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    response = hardened_client.get("/api/v1/fleets", headers={"X-API-Key": "bad-key"})
    assert response.status_code == 401


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
    key_a = hardened_client.post(
        f"/api/v1/fleets/{fleet_a['id']}/api-keys",
        json={"name": "a"},
        headers={"X-API-Key": "admin-secret"},
    ).json()["api_key"]
    response = hardened_client.get(
        f"/api/v1/fleets/{fleet_b['id']}",
        headers={"X-API-Key": key_a},
    )
    assert response.status_code == 403


def test_alert_transition_creates_audit_log(db_session):
    from backend.app.services import alert_service

    db = db_session
    fleet = fleet_service.create_fleet(db, name="Audit Fleet")
    sat = fleet_service.add_satellite(db, fleet.id, name="S1", norad_id=90001, tle=DEMO_SAT)
    from backend.app.db.models import ConjunctionAlert

    alert = ConjunctionAlert(
        fleet_id=fleet.id,
        satellite_id=sat.id,
        debris_norad_id=12345,
        debris_name="DEB",
        tca=datetime.now(timezone.utc),
        pc=1e-4,
        miss_distance_km=1.0,
        risk_level="high",
        status="open",
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    alert_service.transition_alert(db, alert.id, new_status="acknowledged", comment="seen")
    logs, total = audit_service.list_audit_logs(db, fleet_id=fleet.id)
    assert total == 1
    assert logs[0].action == "alert.transition"


def test_tle_update_creates_audit_log(db_session):
    db = db_session
    fleet = fleet_service.create_fleet(db, name="TLE Fleet")
    sat = fleet_service.add_satellite(db, fleet.id, name="S1", norad_id=90002, tle=DEMO_SAT)
    fleet_service.update_satellite(db, sat.id, tle=DEMO_SAT)
    logs, total = audit_service.list_audit_logs(db, fleet_id=fleet.id)
    assert total == 0
    fleet_service.update_satellite(
        db,
        sat.id,
        tle=(SAMPLES / "demo-debris.tle").read_text(encoding="utf-8").strip(),
    )
    logs, total = audit_service.list_audit_logs(db, fleet_id=fleet.id)
    assert total == 1
    assert logs[0].action == "satellite.tle_update"


def test_schedule_crud_creates_audit_logs(db_session):
    db = db_session
    fleet = fleet_service.create_fleet(db, name="Sched Fleet")
    schedule = screening_service.create_schedule(
        db,
        fleet_id=fleet.id,
        name="Daily",
        cron_expression="0 0 * * *",
    )
    screening_service.update_schedule(db, schedule.id, threshold_km=10.0)
    screening_service.delete_schedule(db, schedule.id)
    logs, total = audit_service.list_audit_logs(db, fleet_id=fleet.id)
    assert total == 3
    actions = {log.action for log in logs}
    assert actions == {"schedule.create", "schedule.update", "schedule.delete"}


def test_ops_audit_endpoint(hardened_client):
    fleet = hardened_client.post("/api/v1/fleets", json={"name": "Ops Audit"}).json()
    hardened_client.post(
        "/api/v1/screening/schedules",
        json={
            "fleet_id": fleet["id"],
            "name": "Hourly",
            "cron_expression": "0 * * * *",
        },
    )
    response = hardened_client.get(f"/api/v1/ops/audit?fleet_id={fleet['id']}")
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_health_includes_checks(hardened_client, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    reset_engine_for_tests()
    from backend.app.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "checks" in data
    assert data["checks"]["postgres"] in ("ok", "error", "skipped")
    assert data["checks"]["redis"] in ("ok", "error", "skipped")
    assert data["checks"]["worker"] in ("ok", "error", "skipped")
    assert data["status"] in ("ok", "degraded")
    reset_engine_for_tests()


@patch("backend.app.services.health_checks._check_worker", return_value="skipped")
def test_health_worker_skipped_in_tests(mock_worker, hardened_client):
    response = hardened_client.get("/health")
    assert response.status_code == 200
    assert response.json()["checks"]["worker"] == "skipped"


def test_first_api_key_requires_admin(hardened_client, monkeypatch):
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")
    fleet = hardened_client.post(
        "/api/v1/fleets",
        json={"name": "Bootstrap Fleet"},
        headers={"X-API-Key": "admin-secret"},
    ).json()
    response = hardened_client.post(
        f"/api/v1/fleets/{fleet['id']}/api-keys",
        json={"name": "first"},
    )
    assert response.status_code == 401


def test_purge_old_audit_logs(db_session, monkeypatch):
    monkeypatch.setenv("AUDIT_LOG_RETENTION_DAYS", "90")
    db = db_session
    fleet = fleet_service.create_fleet(db, name="Purge Fleet")
    audit_service.log_audit(
        db,
        fleet_id=fleet.id,
        action="test.action",
        resource_type="fleet",
        resource_id=fleet.id,
        detail={},
    )
    db.commit()
    deleted = audit_service.purge_old_audit_logs(db)
    assert deleted == 0
