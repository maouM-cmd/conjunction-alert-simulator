"""Tests for per-fleet API availability SLO (Phase 10N)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import Base
from backend.app.db.session import get_engine, reset_engine_for_tests
from backend.app.services import api_availability_service, fleet_api_availability_service


@pytest.fixture(autouse=True)
def reset_availability():
    api_availability_service.reset_availability_for_tests()
    yield
    api_availability_service.reset_availability_for_tests()


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


def test_fleet_api_slo_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SLA_FLEET_API_SLO_ENABLED", raising=False)
    assert fleet_api_availability_service.fleet_api_slo_enabled() is False
    summary = fleet_api_availability_service.compute_fleet_api_availability(uuid.uuid4())
    assert summary is None


def test_fleet_buckets_isolated(monkeypatch):
    monkeypatch.setenv("SLA_FLEET_API_SLO_ENABLED", "true")
    fleet_a = uuid.uuid4()
    fleet_b = uuid.uuid4()
    for _ in range(10):
        fleet_api_availability_service.record_fleet_http_status(fleet_a, 200)
    for _ in range(2):
        fleet_api_availability_service.record_fleet_http_status(fleet_a, 500)
    for _ in range(5):
        fleet_api_availability_service.record_fleet_http_status(fleet_b, 200)

    summary_a = fleet_api_availability_service.compute_fleet_api_availability(fleet_a)
    summary_b = fleet_api_availability_service.compute_fleet_api_availability(fleet_b)
    assert summary_a is not None and summary_b is not None
    assert summary_a.request_count == 12
    assert summary_a.errors_5xx == 2
    assert summary_b.request_count == 5
    assert summary_b.errors_5xx == 0


def _create_fleet_with_key(client: TestClient, monkeypatch, name: str) -> tuple[str, str]:
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")
    fleet = client.post(
        "/api/v1/fleets",
        json={"name": name},
        headers={"X-API-Key": "admin-secret"},
    ).json()
    key = client.post(
        f"/api/v1/fleets/{fleet['id']}/api-keys",
        json={"name": f"{name} key"},
        headers={"X-API-Key": "admin-secret"},
    ).json()["api_key"]
    return fleet["id"], key


def test_ops_sla_includes_fleet_api_fields(hardened_client, monkeypatch):
    monkeypatch.setenv("SLA_FLEET_API_SLO_ENABLED", "true")
    fleet_id, fleet_key = _create_fleet_with_key(hardened_client, monkeypatch, "Fleet API SLO")

    for _ in range(20):
        hardened_client.get(f"/api/v1/fleets/{fleet_id}", headers={"X-API-Key": fleet_key})
    hardened_client.get("/nonexistent-fleet-api-slo-path")

    sla = hardened_client.get(
        f"/api/v1/ops/sla?fleet_id={fleet_id}",
        headers={"X-API-Key": "admin-secret"},
    )
    assert sla.status_code == 200
    item = sla.json()["items"][0]
    assert item["fleet_api_request_count"] == 20
    assert item["fleet_api_slo_ok"] is True
    assert item["fleet_api_availability_ratio"] == 1.0


def test_fleet_api_history_endpoint(hardened_client, monkeypatch):
    monkeypatch.setenv("SLA_FLEET_API_SLO_ENABLED", "true")
    fleet_id, fleet_key = _create_fleet_with_key(hardened_client, monkeypatch, "Fleet History")

    for _ in range(5):
        hardened_client.get(f"/api/v1/fleets/{fleet_id}", headers={"X-API-Key": fleet_key})

    response = hardened_client.get(
        f"/api/v1/ops/sla/api-history?days=7&fleet_id={fleet_id}",
        headers={"X-API-Key": "admin-secret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["days"] == 7
    sampled = [item for item in body["items"] if item["request_count"] > 0]
    assert sampled
    assert sampled[0]["request_count"] >= 5


def test_prometheus_exports_fleet_api_slo_gauges(ops_client, monkeypatch):
    monkeypatch.setenv("SLA_FLEET_API_SLO_ENABLED", "true")
    fleet_id = uuid.uuid4()
    for _ in range(10):
        fleet_api_availability_service.record_fleet_http_status(fleet_id, 200)

    response = ops_client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "cas_fleet_api_availability_ratio" in body
    assert "cas_fleet_api_slo_ok" in body
    assert str(fleet_id) in body
