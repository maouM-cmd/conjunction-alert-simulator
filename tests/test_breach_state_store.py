"""Tests for Redis shared breach state (Phase 10V)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

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
