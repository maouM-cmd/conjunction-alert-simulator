"""Tests for Redis shared breach state (Phase 10V)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.services import alertmanager_push_service, breach_state_store


@pytest.fixture(autouse=True)
def reset_breach_state():
    breach_state_store.reset_breach_state_for_tests()
    yield
    breach_state_store.reset_breach_state_for_tests()


def test_breach_redis_state_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ALERTMANAGER_PUSH_REDIS_STATE_ENABLED", raising=False)
    assert breach_state_store.breach_redis_state_enabled() is False


def test_memory_fallback_get_set(monkeypatch):
    monkeypatch.delenv("ALERTMANAGER_PUSH_REDIS_STATE_ENABLED", raising=False)
    monkeypatch.delenv("ALERTMANAGER_PUSH_DB_STATE_ENABLED", raising=False)
    fleet_id = str(uuid.uuid4())
    alertname = "CASFleetOpenAlertsHigh"
    assert breach_state_store.get_breach_state(fleet_id, alertname) is False
    breach_state_store.set_breach_state(fleet_id, alertname, True)
    assert breach_state_store.get_breach_state(fleet_id, alertname) is True
    breach_state_store.set_breach_state(fleet_id, alertname, False)
    assert breach_state_store.get_breach_state(fleet_id, alertname) is False


def test_redis_shared_state_across_instances(monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_PUSH_REDIS_STATE_ENABLED", "true")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    storage: dict[str, str] = {}
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.get.side_effect = lambda key: storage.get(key)
    mock_redis.set.side_effect = lambda key, value: storage.update({key: value})
    mock_redis.scan_iter.return_value = list(storage.keys())

    fleet_id = str(uuid.uuid4())
    alertname = "CASFleetHighRiskOpenAlerts"

    with patch("redis.from_url", return_value=mock_redis):
        breach_state_store.reset_redis_client_for_tests()
        breach_state_store.set_breach_state(fleet_id, alertname, True)

        breach_state_store.reset_redis_client_for_tests()
        assert breach_state_store.get_breach_state(fleet_id, alertname) is True


@patch("backend.app.services.alertmanager_push_service.push_alerts")
def test_sync_breaches_uses_store_only_on_change(mock_push, monkeypatch):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_PUSH_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    monkeypatch.setenv("FLEET_ALERT_OPEN_THRESHOLD", "1")
    monkeypatch.delenv("ALERTMANAGER_PUSH_REDIS_STATE_ENABLED", raising=False)

    fleet_id = uuid.uuid4()
    counts = {
        fleet_id: {
            "open": 5,
            "escalated": 0,
            "acknowledged": 0,
            "mitigation_planned": 0,
            "closed": 0,
            "false_positive": 0,
        }
    }
    risk_counts = {fleet_id: {"high": {"open": 0}, "medium": {"open": 0}, "low": {"open": 0}}}
    fleet_names = {fleet_id: "Store Fleet"}

    alertmanager_push_service.sync_breaches(counts, risk_counts, fleet_names)
    alertmanager_push_service.sync_breaches(counts, risk_counts, fleet_names)

    assert mock_push.call_count == 1


def test_breach_db_state_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ALERTMANAGER_PUSH_DB_STATE_ENABLED", raising=False)
    assert breach_state_store.breach_db_state_enabled() is False


def test_db_shared_state_persists(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("ALERTMANAGER_PUSH_DB_STATE_ENABLED", "true")
    monkeypatch.delenv("ALERTMANAGER_PUSH_REDIS_STATE_ENABLED", raising=False)

    from backend.app.db.models import Base
    from backend.app.db.session import get_engine, get_session_factory, reset_engine_for_tests
    from backend.app.services.fleet_service import create_fleet

    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    factory = get_session_factory()
    assert factory is not None
    db = factory()
    try:
        fleet = create_fleet(db, name="Breach DB Fleet")
        fleet_id = str(fleet.id)
    finally:
        db.close()

    alertname = "CASFleetOpenAlertsHigh"
    breach_state_store.set_breach_state(fleet_id, alertname, True)
    assert breach_state_store.get_breach_state(fleet_id, alertname) is True
    breach_state_store.set_breach_state(fleet_id, alertname, False)
    assert breach_state_store.get_breach_state(fleet_id, alertname) is False
    reset_engine_for_tests()


def test_redis_takes_priority_over_db(monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_PUSH_DB_STATE_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_PUSH_REDIS_STATE_ENABLED", "true")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    fleet_id = str(uuid.uuid4())
    alertname = "CASFleetOpenAlertsHigh"
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = "0"

    with (
        patch("redis.from_url", return_value=mock_redis),
        patch.object(breach_state_store, "_get_db_state") as mock_db_get,
    ):
        breach_state_store.reset_redis_client_for_tests()
        assert breach_state_store.get_breach_state(fleet_id, alertname) is False
        mock_db_get.assert_not_called()


def test_should_sync_breaches_on_metrics_scrape(monkeypatch):
    monkeypatch.delenv("ALERTMANAGER_PUSH_CELERY_ENABLED", raising=False)
    monkeypatch.delenv("ALERTMANAGER_PUSH_REDIS_STATE_ENABLED", raising=False)
    monkeypatch.delenv("ALERTMANAGER_PUSH_DB_STATE_ENABLED", raising=False)
    assert alertmanager_push_service.should_sync_breaches_on_metrics_scrape() is True

    monkeypatch.setenv("ALERTMANAGER_PUSH_CELERY_ENABLED", "true")
    assert alertmanager_push_service.should_sync_breaches_on_metrics_scrape() is False

    monkeypatch.setenv("ALERTMANAGER_PUSH_REDIS_STATE_ENABLED", "true")
    assert alertmanager_push_service.should_sync_breaches_on_metrics_scrape() is True

    monkeypatch.delenv("ALERTMANAGER_PUSH_REDIS_STATE_ENABLED", raising=False)
    monkeypatch.setenv("ALERTMANAGER_PUSH_DB_STATE_ENABLED", "true")
    assert alertmanager_push_service.should_sync_breaches_on_metrics_scrape() is True


def test_list_fleet_breach_states(monkeypatch):
    monkeypatch.delenv("ALERTMANAGER_PUSH_REDIS_STATE_ENABLED", raising=False)
    monkeypatch.delenv("ALERTMANAGER_PUSH_DB_STATE_ENABLED", raising=False)

    fleet_id = str(uuid.uuid4())
    breach_state_store.set_breach_state(fleet_id, "CASFleetOpenAlertsHigh", True)
    breach_state_store.set_breach_state(fleet_id, "CASFleetHighRiskOpenAlerts", False)

    items = breach_state_store.list_fleet_breach_states(fleet_id)
    assert len(items) == 2
    assert items[0].alertname == "CASFleetOpenAlertsHigh"
    assert items[0].is_breaching is True
    assert items[1].alertname == "CASFleetHighRiskOpenAlerts"
    assert items[1].is_breaching is False
    assert breach_state_store.breach_state_backend() == "memory"


def test_breach_state_backend_db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("ALERTMANAGER_PUSH_DB_STATE_ENABLED", "true")
    monkeypatch.delenv("ALERTMANAGER_PUSH_REDIS_STATE_ENABLED", raising=False)

    from backend.app.db.models import Base
    from backend.app.db.session import get_engine, reset_engine_for_tests

    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    try:
        assert breach_state_store.breach_state_backend() == "db"
    finally:
        reset_engine_for_tests()


@pytest.fixture
def ops_client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    from backend.app.db.models import Base
    from backend.app.db.session import get_engine, reset_engine_for_tests

    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    from backend.app.main import app

    with TestClient(app) as client:
        yield client
    reset_engine_for_tests()


def test_breach_states_endpoint(ops_client, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_PUSH_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")
    monkeypatch.delenv("ALERTMANAGER_PUSH_REDIS_STATE_ENABLED", raising=False)
    monkeypatch.delenv("ALERTMANAGER_PUSH_DB_STATE_ENABLED", raising=False)

    fleet_id = str(uuid.uuid4())
    breach_state_store.set_breach_state(fleet_id, "CASFleetOpenAlertsHigh", True)

    response = ops_client.get(
        f"/api/v1/ops/prometheus/alertmanager/breach-states?fleet_id={fleet_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["fleet_id"] == fleet_id
    assert data["backend"] == "memory"
    assert data["total"] == 2
    assert data["items"][0]["alertname"] == "CASFleetOpenAlertsHigh"
    assert data["items"][0]["is_breaching"] is True
    assert data["items"][1]["is_breaching"] is False


def test_breach_states_disabled_returns_503(ops_client, monkeypatch):
    monkeypatch.delenv("ALERTMANAGER_PUSH_ENABLED", raising=False)
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")
    fleet_id = str(uuid.uuid4())
    response = ops_client.get(
        f"/api/v1/ops/prometheus/alertmanager/breach-states?fleet_id={fleet_id}"
    )
    assert response.status_code == 503


def test_breach_manual_override_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ALERTMANAGER_BREACH_STATE_MANUAL_OVERRIDE_ENABLED", raising=False)
    assert breach_state_store.breach_manual_override_enabled() is False


def test_list_all_fleet_breach_states(ops_client, monkeypatch):
    monkeypatch.delenv("ALERTMANAGER_PUSH_REDIS_STATE_ENABLED", raising=False)
    monkeypatch.delenv("ALERTMANAGER_PUSH_DB_STATE_ENABLED", raising=False)

    from backend.app.services.fleet_service import create_fleet

    from backend.app.db.session import get_session_factory

    factory = get_session_factory()
    assert factory is not None
    db = factory()
    try:
        fleet_a = create_fleet(db, name="Breach Fleet A")
        fleet_b = create_fleet(db, name="Breach Fleet B")
        db.commit()
        fleet_a_id = str(fleet_a.id)
        fleet_b_id = str(fleet_b.id)
        breach_state_store.set_breach_state(fleet_a_id, "CASFleetOpenAlertsHigh", True)
        rows = breach_state_store.list_all_fleet_breach_states(db)
        assert len(rows) == 4
        by_key = {(r.fleet_id, r.alertname): r for r in rows}
        assert by_key[(fleet_a_id, "CASFleetOpenAlertsHigh")].is_breaching is True
        assert by_key[(fleet_a_id, "CASFleetOpenAlertsHigh")].fleet_name == "Breach Fleet A"
        assert by_key[(fleet_b_id, "CASFleetOpenAlertsHigh")].is_breaching is False
    finally:
        db.close()


def test_breach_states_admin_list_all(ops_client, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_PUSH_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")

    from backend.app.services.fleet_service import create_fleet
    from backend.app.db.session import get_session_factory

    factory = get_session_factory()
    db = factory()
    try:
        fleet = create_fleet(db, name="Admin Breach Fleet")
        db.commit()
        fleet_id = str(fleet.id)
    finally:
        db.close()

    breach_state_store.set_breach_state(fleet_id, "CASFleetHighRiskOpenAlerts", True)
    response = ops_client.get(
        "/api/v1/ops/prometheus/alertmanager/breach-states",
        headers={"X-API-Key": "admin-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert "fleet_id" not in data
    match = [item for item in data["items"] if item["fleet_id"] == fleet_id]
    assert len(match) == 2
    high_risk = next(i for i in match if i["alertname"] == "CASFleetHighRiskOpenAlerts")
    assert high_risk["is_breaching"] is True


def test_breach_states_admin_list_forbidden_for_fleet_key(ops_client, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_PUSH_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")

    from backend.app.services import api_key_service
    from backend.app.services.fleet_service import create_fleet
    from backend.app.db.session import get_session_factory

    factory = get_session_factory()
    db = factory()
    try:
        fleet = create_fleet(db, name="Fleet Key Breach")
        db.commit()
        _, plain = api_key_service.create_api_key(db, fleet_id=fleet.id, name="ops")
        db.commit()
    finally:
        db.close()

    response = ops_client.get(
        "/api/v1/ops/prometheus/alertmanager/breach-states",
        headers={"X-API-Key": plain},
    )
    assert response.status_code == 403


def test_breach_state_manual_override(ops_client, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_PUSH_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    monkeypatch.setenv("ALERTMANAGER_BREACH_STATE_MANUAL_OVERRIDE_ENABLED", "true")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")

    from backend.app.db.models import AuditLog
    from backend.app.services.fleet_service import create_fleet
    from backend.app.db.session import get_session_factory

    factory = get_session_factory()
    db = factory()
    try:
        fleet = create_fleet(db, name="Override Fleet")
        db.commit()
        fleet_id = str(fleet.id)
    finally:
        db.close()

    response = ops_client.put(
        "/api/v1/ops/prometheus/alertmanager/breach-states",
        json={
            "fleet_id": fleet_id,
            "alertname": "CASFleetOpenAlertsHigh",
            "is_breaching": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["manual_override_enabled"] is True
    assert data["items"][0]["is_breaching"] is True
    assert breach_state_store.get_breach_state(fleet_id, "CASFleetOpenAlertsHigh") is True

    db = factory()
    try:
        audits = db.query(AuditLog).filter(AuditLog.action == "alert.breach_state_manual_override").all()
        assert len(audits) == 1
        assert audits[0].detail["alertname"] == "CASFleetOpenAlertsHigh"
    finally:
        db.close()


def test_breach_state_manual_override_disabled_returns_503(ops_client, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_PUSH_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    monkeypatch.delenv("ALERTMANAGER_BREACH_STATE_MANUAL_OVERRIDE_ENABLED", raising=False)
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")

    fleet_id = str(uuid.uuid4())
    response = ops_client.put(
        "/api/v1/ops/prometheus/alertmanager/breach-states",
        json={
            "fleet_id": fleet_id,
            "alertname": "CASFleetOpenAlertsHigh",
            "is_breaching": True,
        },
    )
    assert response.status_code == 503


def test_breach_sticky_override_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ALERTMANAGER_BREACH_STATE_STICKY_OVERRIDE_ENABLED", raising=False)
    assert breach_state_store.breach_sticky_override_enabled() is False


@patch("backend.app.services.alertmanager_push_service.push_alerts")
def test_sticky_override_blocks_sync_breaches(mock_push, monkeypatch):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_PUSH_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    monkeypatch.setenv("ALERTMANAGER_BREACH_STATE_STICKY_OVERRIDE_ENABLED", "true")
    monkeypatch.delenv("ALERTMANAGER_PUSH_REDIS_STATE_ENABLED", raising=False)
    monkeypatch.delenv("ALERTMANAGER_PUSH_DB_STATE_ENABLED", raising=False)

    fleet_id = uuid.uuid4()
    breach_state_store.set_breach_state(str(fleet_id), "CASFleetOpenAlertsHigh", False)
    breach_state_store.set_sticky_override(str(fleet_id), "CASFleetOpenAlertsHigh", True)

    counts = {
        fleet_id: {
            "open": 99,
            "escalated": 0,
            "acknowledged": 0,
            "mitigation_planned": 0,
            "closed": 0,
            "false_positive": 0,
        }
    }
    risk_counts = {fleet_id: {"high": {"open": 0}, "medium": {"open": 0}, "low": {"open": 0}}}
    fleet_names = {fleet_id: "Sticky Fleet"}

    alertmanager_push_service.sync_breaches(counts, risk_counts, fleet_names)
    mock_push.assert_not_called()
    assert breach_state_store.get_breach_state(str(fleet_id), "CASFleetOpenAlertsHigh") is False


@patch("backend.app.services.alertmanager_push_service.push_alerts")
def test_breach_state_sticky_put_and_clear(mock_push, ops_client, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_PUSH_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    monkeypatch.setenv("ALERTMANAGER_BREACH_STATE_MANUAL_OVERRIDE_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_BREACH_STATE_STICKY_OVERRIDE_ENABLED", "true")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")

    from backend.app.db.models import AuditLog
    from backend.app.services.fleet_service import create_fleet
    from backend.app.db.session import get_session_factory

    factory = get_session_factory()
    db = factory()
    try:
        fleet = create_fleet(db, name="Sticky Override Fleet")
        db.commit()
        fleet_id = str(fleet.id)
    finally:
        db.close()

    response = ops_client.put(
        "/api/v1/ops/prometheus/alertmanager/breach-states",
        json={
            "fleet_id": fleet_id,
            "alertname": "CASFleetOpenAlertsHigh",
            "is_breaching": True,
            "sticky": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sticky_override_enabled"] is True
    assert data["items"][0]["is_sticky"] is True
    assert breach_state_store.is_sticky_override(fleet_id, "CASFleetOpenAlertsHigh") is True

    response = ops_client.delete(
        "/api/v1/ops/prometheus/alertmanager/breach-states/sticky"
        f"?fleet_id={fleet_id}&alertname=CASFleetOpenAlertsHigh"
    )
    assert response.status_code == 200
    assert breach_state_store.is_sticky_override(fleet_id, "CASFleetOpenAlertsHigh") is False

    db = factory()
    try:
        cleared = db.query(AuditLog).filter(AuditLog.action == "alert.breach_state_sticky_cleared").all()
        assert len(cleared) == 1
    finally:
        db.close()
