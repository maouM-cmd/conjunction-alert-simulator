"""Tests for webhook alert notifier."""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.conjunction import ConjunctionEvent
from backend.app.services.tle_parser import parse_tle
from backend.app.services.webhook_notifier import (
    DEFAULT_PC_THRESHOLD,
    notify_conjunction_events,
    send_test_webhook,
)

SAMPLES = __import__("pathlib").Path(__file__).resolve().parents[1] / "samples"
DEMO_SAT = (SAMPLES / "demo-satellite.tle").read_text(encoding="utf-8").strip()

client = TestClient(app)


def _sample_event(pc: float, risk: str = "high") -> ConjunctionEvent:
    return ConjunctionEvent(
        debris_norad_id=99999,
        debris_name="TEST DEB",
        debris_tle="1 99999U ...",
        tca=datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc),
        miss_distance_km=0.5,
        relative_velocity_kms=7.0,
        risk_level=risk,
        pc=pc,
    )


def test_notify_without_url_is_noop():
    with patch.dict(os.environ, {"ALERT_WEBHOOK_URL": ""}, clear=False):
        sat = parse_tle(DEMO_SAT)
        result = notify_conjunction_events(sat, [_sample_event(1e-3)])
        assert result.sent is False
        assert result.degraded is False


def test_notify_filters_by_threshold():
    with patch.dict(
        os.environ,
        {"ALERT_WEBHOOK_URL": "https://example.com/hook", "ALERT_PC_THRESHOLD": "1e-4"},
        clear=False,
    ):
        sat = parse_tle(DEMO_SAT)
        result = notify_conjunction_events(
            sat,
            [_sample_event(1e-6, "medium"), _sample_event(1e-3, "high")],
        )
        assert result.alert_count == 1


@patch("backend.app.services.webhook_notifier.httpx.Client")
def test_send_test_webhook_success(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    with patch.dict(os.environ, {"ALERT_WEBHOOK_URL": "https://example.com/hook"}, clear=False):
        result = send_test_webhook()
        assert result.sent is True
        assert result.degraded is False
        mock_client.post.assert_called_once()


def test_webhook_test_endpoint_without_url_returns_503():
    with patch.dict(os.environ, {"ALERT_WEBHOOK_URL": ""}, clear=False):
        response = client.post("/api/v1/alerts/webhook/test")
        assert response.status_code == 503


@patch("backend.app.services.webhook_notifier.httpx.Client")
def test_webhook_test_endpoint_success(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    with patch.dict(os.environ, {"ALERT_WEBHOOK_URL": "https://example.com/hook"}, clear=False):
        response = client.post("/api/v1/alerts/webhook/test")
        assert response.status_code == 200
        data = response.json()
        assert data["sent"] is True


def test_default_pc_threshold():
    assert DEFAULT_PC_THRESHOLD == 1e-5
