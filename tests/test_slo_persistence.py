"""Tests for API SLO DB persistence (Phase 10J)."""

from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import ApiSloHourlyBucket, Base
from backend.app.db.session import get_engine, reset_engine_for_tests
from backend.app.services import api_availability_service, slo_persistence_service


@pytest.fixture(autouse=True)
def reset_availability():
    api_availability_service.reset_availability_for_tests()
    yield
    api_availability_service.reset_availability_for_tests()


@pytest.fixture
def db_client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    from backend.app.main import app

    with TestClient(app) as client:
        yield client
    reset_engine_for_tests()


def test_persist_off_uses_memory_only(monkeypatch):
    monkeypatch.setenv("SLA_API_PERSIST_ENABLED", "false")
    for _ in range(5):
        api_availability_service.record_http_status(200)
    summary = api_availability_service.compute_api_availability()
    assert summary.request_count == 5


def test_persist_on_writes_bucket(db_client, monkeypatch):
    monkeypatch.setenv("SLA_API_PERSIST_ENABLED", "true")
    for _ in range(12):
        api_availability_service.record_http_status(200)
    for _ in range(2):
        api_availability_service.record_http_status(500)

    from backend.app.db.session import get_session_factory

    factory = get_session_factory()
    assert factory is not None
    db = factory()
    try:
        rows = db.query(ApiSloHourlyBucket).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.request_total == 14
        assert row.errors_5xx == 2
    finally:
        db.close()

    summary = api_availability_service.compute_api_availability()
    assert summary.request_count == 14
    assert summary.errors_5xx == 2
    assert summary.slo_ok is False


def test_restart_simulation_hydrate_preserves_availability(db_client, monkeypatch):
    monkeypatch.setenv("SLA_API_PERSIST_ENABLED", "true")
    for _ in range(20):
        api_availability_service.record_http_status(200)

    api_availability_service.replace_memory_buckets([])

    from backend.app.db.session import get_session_factory

    factory = get_session_factory()
    db = factory()
    try:
        slo_persistence_service.hydrate_memory_from_db(db)
    finally:
        db.close()

    memory = api_availability_service.load_memory_buckets()
    assert sum(bucket[1] for bucket in memory) == 20

    summary = api_availability_service.compute_api_availability()
    assert summary.request_count == 20
    assert summary.availability_ratio == 1.0


def test_rollup_daily_groups_by_utc_day(monkeypatch):
    monkeypatch.setenv("SLA_API_TARGET_PERCENT", "99.9")
    day1 = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    day2 = datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)
    buckets = {
        int(day1.timestamp()): (100, 1),
        int(day1.timestamp()) + 3600: (50, 0),
        int(day2.timestamp()): (200, 0),
    }
    rolled = slo_persistence_service.rollup_daily(buckets)
    assert len(rolled) == 2
    assert rolled[0].request_count == 150
    assert rolled[0].errors_5xx == 1
    assert rolled[1].request_count == 200
    assert rolled[1].slo_ok is True


def test_api_history_endpoint(db_client, monkeypatch):
    monkeypatch.setenv("SLA_API_PERSIST_ENABLED", "true")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")
    for _ in range(8):
        api_availability_service.record_http_status(200)

    response = db_client.get("/api/v1/ops/sla/api-history?days=7")
    assert response.status_code == 200
    body = response.json()
    assert body["days"] == 7
    assert body["target_percent"] == 99.9
    assert len(body["items"]) == 7
    assert "availability_ratio" in body["items"][-1]
    assert "slo_ok" in body["items"][-1]


def test_api_history_requires_admin_when_auth_enabled(db_client, monkeypatch):
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")
    response = db_client.get("/api/v1/ops/sla/api-history?days=7")
    assert response.status_code == 401

    response = db_client.get(
        "/api/v1/ops/sla/api-history?days=7",
        headers={"X-API-Key": "admin-secret"},
    )
    assert response.status_code == 200


def test_retention_prune_removes_old_buckets(db_client, monkeypatch):
    monkeypatch.setenv("SLA_API_PERSIST_ENABLED", "true")
    monkeypatch.setenv("SLA_API_RETENTION_DAYS", "7")

    from backend.app.db.session import get_session_factory

    factory = get_session_factory()
    db = factory()
    try:
        old_epoch = int(time.time()) - 10 * 86400
        old_epoch -= old_epoch % 3600
        db.add(
            ApiSloHourlyBucket(
                hour_epoch=old_epoch,
                request_total=5,
                errors_5xx=0,
                updated_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        removed = slo_persistence_service.prune_old_buckets(db)
        assert removed == 1
        assert db.get(ApiSloHourlyBucket, old_epoch) is None
    finally:
        db.close()


def test_compute_db_based_slo_ok(db_client, monkeypatch):
    monkeypatch.setenv("SLA_API_PERSIST_ENABLED", "true")
    monkeypatch.setenv("SLA_API_TARGET_PERCENT", "99.9")
    for _ in range(1000):
        api_availability_service.record_http_status(200)
    summary = api_availability_service.compute_api_availability()
    assert summary.slo_ok is True
    assert summary.availability_ratio == 1.0
