"""Tests for Alertmanager silences API (Phase 10T)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import Base
from backend.app.db.session import get_engine, reset_engine_for_tests
from backend.app.services import alertmanager_silence_service


@pytest.fixture
def ops_client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    from backend.app.main import app

    with TestClient(app) as client:
        yield client
    reset_engine_for_tests()


@patch("backend.app.services.alertmanager_silence_service.httpx.Client")
def test_create_fleet_silence(mock_client_cls, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_SILENCES_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"silenceID": "silence-123"}
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    fleet_id = uuid.uuid4()
    result = alertmanager_silence_service.create_fleet_silence(
        fleet_id,
        alertname="CASFleetOpenAlertsHigh",
        duration_hours=2,
        comment="test",
    )
    assert result.ok is True
    assert result.silence_id == "silence-123"
    assert mock_client.post.call_count == 1


@patch("backend.app.services.alertmanager_silence_service.httpx.Client")
def test_list_silences_filters_by_fleet(mock_client_cls, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_SILENCES_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")

    fleet_a = str(uuid.uuid4())
    fleet_b = str(uuid.uuid4())
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = [
        {
            "id": "1",
            "matchers": [{"name": "fleet_id", "value": fleet_a}],
            "status": {"startsAt": "2026-06-28T00:00:00.000Z", "endsAt": "2026-06-28T04:00:00.000Z"},
            "comment": "a",
        },
        {
            "id": "2",
            "matchers": [{"name": "fleet_id", "value": fleet_b}],
            "status": {"startsAt": "2026-06-28T00:00:00.000Z", "endsAt": "2026-06-28T04:00:00.000Z"},
            "comment": "b",
        },
    ]
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response
    mock_client_cls.return_value = mock_client

    items, error = alertmanager_silence_service.list_silences(uuid.UUID(fleet_a))
    assert error is None
    assert len(items) == 1
    assert items[0].fleet_id == fleet_a


def test_create_silence_endpoint(ops_client, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_SILENCES_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")

    fleet_id = str(uuid.uuid4())
    with patch(
        "backend.app.services.alertmanager_silence_service.create_fleet_silence",
        return_value=alertmanager_silence_service.SilenceResult(
            ok=True,
            message="ok",
            silence_id="silence-abc",
        ),
    ):
        response = ops_client.post(
            "/api/v1/ops/prometheus/alertmanager/silences",
            json={"fleet_id": fleet_id, "duration_hours": 4},
        )
    assert response.status_code == 200
    assert response.json()["silence_id"] == "silence-abc"


def test_list_silences_endpoint(ops_client, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_SILENCES_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")

    fleet_id = str(uuid.uuid4())
    item = alertmanager_silence_service.SilenceItem(
        silence_id="silence-1",
        fleet_id=fleet_id,
        alertname="CASFleetOpenAlertsHigh",
        starts_at=None,
        ends_at=None,
        comment="test",
    )
    with patch(
        "backend.app.services.alertmanager_silence_service.list_silences",
        return_value=([item], None),
    ):
        response = ops_client.get(
            f"/api/v1/ops/prometheus/alertmanager/silences?fleet_id={fleet_id}"
        )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["silence_id"] == "silence-1"


def test_silences_disabled_returns_503(ops_client, monkeypatch):
    monkeypatch.delenv("ALERTMANAGER_SILENCES_ENABLED", raising=False)
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")
    response = ops_client.get("/api/v1/ops/prometheus/alertmanager/silences")
    assert response.status_code == 503


@patch("backend.app.services.alertmanager_silence_service.httpx.Client")
def test_delete_silence_service(mock_client_cls, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_SILENCES_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.delete.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = alertmanager_silence_service.delete_silence("silence-del-1")
    assert result.ok is True
    assert result.silence_id == "silence-del-1"
    mock_client.delete.assert_called_once()
    assert "silence-del-1" in mock_client.delete.call_args[0][0]


@patch("backend.app.services.alertmanager_silence_service.httpx.Client")
def test_get_silence_by_id(mock_client_cls, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_SILENCES_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")

    fleet_id = str(uuid.uuid4())
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "silence-xyz",
        "matchers": [
            {"name": "fleet_id", "value": fleet_id},
            {"name": "alertname", "value": "CASFleetOpenAlertsHigh"},
        ],
        "status": {
            "startsAt": "2026-06-28T00:00:00.000Z",
            "endsAt": "2026-06-28T04:00:00.000Z",
        },
        "comment": "maintenance",
    }
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response
    mock_client_cls.return_value = mock_client

    item = alertmanager_silence_service.get_silence("silence-xyz")
    assert item is not None
    assert item.silence_id == "silence-xyz"
    assert item.fleet_id == fleet_id


def test_delete_silence_endpoint(ops_client, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_SILENCES_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")

    fleet_id = str(uuid.uuid4())
    silence = alertmanager_silence_service.SilenceItem(
        silence_id="silence-del-api",
        fleet_id=fleet_id,
        alertname="CASFleetOpenAlertsHigh",
        starts_at=None,
        ends_at=None,
        comment="test",
    )
    with (
        patch(
            "backend.app.services.alertmanager_silence_service.get_silence",
            return_value=silence,
        ),
        patch(
            "backend.app.services.alertmanager_silence_service.delete_silence",
            return_value=alertmanager_silence_service.SilenceResult(
                ok=True,
                message="silence を削除しました。",
                silence_id="silence-del-api",
            ),
        ),
    ):
        response = ops_client.delete(
            "/api/v1/ops/prometheus/alertmanager/silences/silence-del-api"
        )
    assert response.status_code == 200
    assert response.json()["silence_id"] == "silence-del-api"


def test_delete_silence_other_fleet_forbidden(ops_client, monkeypatch):
    from tests.test_fleet_api_slo import _create_fleet_with_key

    monkeypatch.setenv("ALERTMANAGER_SILENCES_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")

    fleet_a, key_a = _create_fleet_with_key(ops_client, monkeypatch, "Silence Fleet A")
    fleet_b = str(uuid.uuid4())
    silence = alertmanager_silence_service.SilenceItem(
        silence_id="silence-other",
        fleet_id=fleet_b,
        alertname="CASFleetOpenAlertsHigh",
        starts_at=None,
        ends_at=None,
        comment="other",
    )
    with patch(
        "backend.app.services.alertmanager_silence_service.get_silence",
        return_value=silence,
    ):
        response = ops_client.delete(
            "/api/v1/ops/prometheus/alertmanager/silences/silence-other",
            headers={"X-API-Key": key_a},
        )
    assert response.status_code == 403
    assert fleet_a != fleet_b


def test_delete_silence_disabled_returns_503(ops_client, monkeypatch):
    monkeypatch.delenv("ALERTMANAGER_SILENCES_ENABLED", raising=False)
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")
    response = ops_client.delete(
        "/api/v1/ops/prometheus/alertmanager/silences/silence-1"
    )
    assert response.status_code == 503


def _silence_item(silence_id: str, fleet_id: str, alertname: str | None = None):
    return alertmanager_silence_service.SilenceItem(
        silence_id=silence_id,
        fleet_id=fleet_id,
        alertname=alertname,
        starts_at=None,
        ends_at=None,
        comment="test",
    )


def test_delete_silences_for_fleet_deletes_all(monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_SILENCES_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")

    fleet_id = uuid.uuid4()
    items = [
        _silence_item("s1", str(fleet_id), "CASFleetOpenAlertsHigh"),
        _silence_item("s2", str(fleet_id)),
    ]
    with (
        patch(
            "backend.app.services.alertmanager_silence_service.list_silences",
            return_value=(items, None),
        ),
        patch(
            "backend.app.services.alertmanager_silence_service.delete_silence",
            side_effect=lambda sid: alertmanager_silence_service.SilenceResult(
                ok=True,
                message="ok",
                silence_id=sid,
            ),
        ) as mock_delete,
    ):
        result = alertmanager_silence_service.delete_silences_for_fleet(fleet_id)
    assert result.ok is True
    assert result.deleted_count == 2
    assert mock_delete.call_count == 2


def test_delete_silences_for_fleet_filters_alertname(monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_SILENCES_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")

    fleet_id = uuid.uuid4()
    items = [
        _silence_item("s1", str(fleet_id), "CASFleetOpenAlertsHigh"),
        _silence_item("s2", str(fleet_id), "CASFleetHighRiskOpenAlerts"),
    ]
    with (
        patch(
            "backend.app.services.alertmanager_silence_service.list_silences",
            return_value=(items, None),
        ),
        patch(
            "backend.app.services.alertmanager_silence_service.delete_silence",
            side_effect=lambda sid: alertmanager_silence_service.SilenceResult(
                ok=True,
                message="ok",
                silence_id=sid,
            ),
        ) as mock_delete,
    ):
        result = alertmanager_silence_service.delete_silences_for_fleet(
            fleet_id,
            alertname="CASFleetOpenAlertsHigh",
        )
    assert result.deleted_count == 1
    assert result.silence_ids == ("s1",)
    assert mock_delete.call_count == 1


def test_bulk_delete_silence_endpoint(ops_client, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_SILENCES_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")

    fleet_id = str(uuid.uuid4())
    with patch(
        "backend.app.services.alertmanager_silence_service.delete_silences_for_fleet",
        return_value=alertmanager_silence_service.BulkSilenceResult(
            ok=True,
            message="2 件の silence を削除しました。",
            deleted_count=2,
            silence_ids=("s1", "s2"),
        ),
    ):
        response = ops_client.delete(
            f"/api/v1/ops/prometheus/alertmanager/silences?fleet_id={fleet_id}"
        )
    assert response.status_code == 200
    data = response.json()
    assert data["deleted_count"] == 2
    assert data["silence_ids"] == ["s1", "s2"]


def test_bulk_delete_silence_zero_items(ops_client, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_SILENCES_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")

    fleet_id = str(uuid.uuid4())
    with patch(
        "backend.app.services.alertmanager_silence_service.delete_silences_for_fleet",
        return_value=alertmanager_silence_service.BulkSilenceResult(
            ok=True,
            message="削除対象の silence はありません。",
            deleted_count=0,
        ),
    ):
        response = ops_client.delete(
            f"/api/v1/ops/prometheus/alertmanager/silences?fleet_id={fleet_id}"
        )
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 0


def test_bulk_delete_silence_other_fleet_forbidden(ops_client, monkeypatch):
    from tests.test_fleet_api_slo import _create_fleet_with_key

    monkeypatch.setenv("ALERTMANAGER_SILENCES_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")

    fleet_a, key_a = _create_fleet_with_key(ops_client, monkeypatch, "Bulk Silence Fleet A")
    fleet_b = str(uuid.uuid4())
    response = ops_client.delete(
        f"/api/v1/ops/prometheus/alertmanager/silences?fleet_id={fleet_b}",
        headers={"X-API-Key": key_a},
    )
    assert response.status_code == 403
    assert fleet_a != fleet_b


def test_bulk_delete_silence_disabled_returns_503(ops_client, monkeypatch):
    monkeypatch.delenv("ALERTMANAGER_SILENCES_ENABLED", raising=False)
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")
    fleet_id = str(uuid.uuid4())
    response = ops_client.delete(
        f"/api/v1/ops/prometheus/alertmanager/silences?fleet_id={fleet_id}"
    )
    assert response.status_code == 503
