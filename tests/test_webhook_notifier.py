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
def test_send_test_webhook_slack_format(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    with patch.dict(
        os.environ,
        {
            "ALERT_WEBHOOK_URL": "https://example.com/hook",
            "ALERT_WEBHOOK_FORMAT": "slack",
        },
        clear=False,
    ):
        result = send_test_webhook()
        assert result.sent is True
        payload = mock_client.post.call_args.kwargs["json"]
        assert "text" in payload


@patch("backend.app.services.webhook_notifier.httpx.Client")
def test_notify_slack_payload_has_text(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    with patch.dict(
        os.environ,
        {
            "ALERT_WEBHOOK_URL": "https://example.com/hook",
            "ALERT_WEBHOOK_FORMAT": "slack",
        },
        clear=False,
    ):
        sat = parse_tle(DEMO_SAT)
        notify_conjunction_events(sat, [_sample_event(1e-3)])
        payload = mock_client.post.call_args.kwargs["json"]
        assert "text" in payload
        assert "CAS conjunction alert" in payload["text"]


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


def test_notify_slack_bot_without_token():
    with patch.dict(
        os.environ,
        {"ALERT_WEBHOOK_FORMAT": "slack_bot", "SLACK_BOT_TOKEN": "", "SLACK_CHANNEL_ID": ""},
        clear=False,
    ):
        sat = parse_tle(DEMO_SAT)
        result = notify_conjunction_events(sat, [_sample_event(1e-3)])
        assert result.sent is False
        assert "SLACK_BOT_TOKEN" in result.message


@patch("backend.app.services.webhook_notifier.httpx.Client")
def test_send_test_webhook_slack_bot_success(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"ok": True}
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    with patch.dict(
        os.environ,
        {
            "ALERT_WEBHOOK_FORMAT": "slack_bot",
            "SLACK_BOT_TOKEN": "xoxb-test",
            "SLACK_CHANNEL_ID": "C0123456789",
        },
        clear=False,
    ):
        result = send_test_webhook()
        assert result.sent is True
        assert result.message == "Slack chat.postMessage 成功。"
        call_kwargs = mock_client.post.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer xoxb-test"
        assert call_kwargs["json"] == {
            "channel": "C0123456789",
            "text": "*CAS* webhook test ping",
        }


@patch("backend.app.services.webhook_notifier.httpx.Client")
def test_send_test_webhook_slack_bot_api_error(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"ok": False, "error": "channel_not_found"}
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    with patch.dict(
        os.environ,
        {
            "ALERT_WEBHOOK_FORMAT": "slack_bot",
            "SLACK_BOT_TOKEN": "xoxb-test",
            "SLACK_CHANNEL_ID": "C0123456789",
        },
        clear=False,
    ):
        result = send_test_webhook()
        assert result.sent is False
        assert result.degraded is True
        assert "channel_not_found" in result.message


def test_webhook_test_endpoint_slack_bot_without_token_returns_503():
    with patch.dict(
        os.environ,
        {"ALERT_WEBHOOK_FORMAT": "slack_bot", "SLACK_BOT_TOKEN": "", "SLACK_CHANNEL_ID": ""},
        clear=False,
    ):
        response = client.post("/api/v1/alerts/webhook/test")
        assert response.status_code == 503


SMTP_ENV = {
    "ALERT_WEBHOOK_FORMAT": "smtp",
    "SMTP_HOST": "smtp.example.com",
    "SMTP_PORT": "587",
    "SMTP_FROM": "cas@example.com",
    "SMTP_TO": "ops@example.com",
    "SMTP_USER": "cas@example.com",
    "SMTP_PASSWORD": "secret",
    "SMTP_USE_TLS": "true",
}


def test_notify_smtp_without_host():
    with patch.dict(
        os.environ,
        {"ALERT_WEBHOOK_FORMAT": "smtp", "SMTP_HOST": "", "SMTP_FROM": "", "SMTP_TO": ""},
        clear=False,
    ):
        sat = parse_tle(DEMO_SAT)
        result = notify_conjunction_events(sat, [_sample_event(1e-3)])
        assert result.sent is False
        assert "SMTP_HOST" in result.message


@patch("backend.app.services.webhook_notifier.smtplib.SMTP")
def test_send_test_webhook_smtp_success(mock_smtp_cls):
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)
    mock_smtp_cls.return_value = mock_smtp

    with patch.dict(os.environ, SMTP_ENV, clear=False):
        result = send_test_webhook()
        assert result.sent is True
        assert result.message == "SMTP 送信成功。"
        mock_smtp_cls.assert_called_once_with("smtp.example.com", 587, timeout=10.0)
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("cas@example.com", "secret")
        mock_smtp.send_message.assert_called_once()
        msg = mock_smtp.send_message.call_args.args[0]
        assert msg["Subject"] == "CAS webhook test"
        assert msg["To"] == "ops@example.com"


@patch("backend.app.services.webhook_notifier.smtplib.SMTP")
def test_notify_smtp_payload(mock_smtp_cls):
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)
    mock_smtp_cls.return_value = mock_smtp

    with patch.dict(os.environ, SMTP_ENV, clear=False):
        sat = parse_tle(DEMO_SAT)
        result = notify_conjunction_events(sat, [_sample_event(1e-3)])
        assert result.sent is True
        msg = mock_smtp.send_message.call_args.args[0]
        assert msg["Subject"] == "CAS conjunction alert"
        assert "CAS conjunction alert" in msg.get_content()


@patch("backend.app.services.webhook_notifier.smtplib.SMTP")
def test_send_test_webhook_smtp_failure(mock_smtp_cls):
    import smtplib

    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)
    mock_smtp.starttls.side_effect = smtplib.SMTPException("TLS failed")
    mock_smtp_cls.return_value = mock_smtp

    with patch.dict(os.environ, SMTP_ENV, clear=False):
        result = send_test_webhook()
        assert result.sent is False
        assert result.degraded is True
        assert "TLS failed" in result.message


def test_webhook_test_endpoint_smtp_without_host_returns_503():
    with patch.dict(
        os.environ,
        {"ALERT_WEBHOOK_FORMAT": "smtp", "SMTP_HOST": "", "SMTP_FROM": "", "SMTP_TO": ""},
        clear=False,
    ):
        response = client.post("/api/v1/alerts/webhook/test")
        assert response.status_code == 503


@patch("backend.app.services.webhook_notifier.smtplib.SMTP")
def test_health_smtp_format(mock_smtp_cls):
    with patch.dict(os.environ, SMTP_ENV, clear=False):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["alert_delivery_configured"] is True
        assert data["alert_delivery_format"] == "smtp"


PAGERDUTY_ENV = {
    "ALERT_WEBHOOK_FORMAT": "pagerduty",
    "PAGERDUTY_ROUTING_KEY": "test-routing-key",
}


def test_notify_pagerduty_without_routing_key():
    with patch.dict(
        os.environ,
        {"ALERT_WEBHOOK_FORMAT": "pagerduty", "PAGERDUTY_ROUTING_KEY": ""},
        clear=False,
    ):
        sat = parse_tle(DEMO_SAT)
        result = notify_conjunction_events(sat, [_sample_event(1e-3)])
        assert result.sent is False
        assert "PAGERDUTY_ROUTING_KEY" in result.message


@patch("backend.app.services.webhook_notifier.httpx.Client")
def test_send_test_webhook_pagerduty_success(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 202
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    with patch.dict(os.environ, PAGERDUTY_ENV, clear=False):
        result = send_test_webhook()
        assert result.sent is True
        assert result.message == "PagerDuty Events API 成功。"
        call_args = mock_client.post.call_args
        assert call_args.args[0] == "https://events.pagerduty.com/v2/enqueue"
        body = call_args.kwargs["json"]
        assert body["routing_key"] == "test-routing-key"
        assert body["event_action"] == "trigger"
        assert body["payload"]["severity"] == "info"
        assert body["payload"]["summary"] == "CAS webhook test ping"


@patch("backend.app.services.webhook_notifier.httpx.Client")
def test_notify_pagerduty_severity_error(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 202
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    with patch.dict(os.environ, PAGERDUTY_ENV, clear=False):
        sat = parse_tle(DEMO_SAT)
        notify_conjunction_events(sat, [_sample_event(1e-3, "high")])
        body = mock_client.post.call_args.kwargs["json"]
        assert body["payload"]["severity"] == "error"


@patch("backend.app.services.webhook_notifier.httpx.Client")
def test_notify_pc_escalation_pagerduty_critical(mock_client_cls):
    from uuid import uuid4

    mock_response = MagicMock()
    mock_response.status_code = 202
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    alert_cls = type("ConjunctionAlert", (object,), {})
    refine_cls = type("AlertPcRefinement", (object,), {})
    alert_id = uuid4()
    alert = alert_cls()
    alert.id = alert_id
    alert.debris_name = "DEB"
    alert.debris_norad_id = 99999
    alert.tca = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
    alert.satellite = type("Sat", (object,), {"name": "SAT", "norad_id": 25544})()
    refinement = refine_cls()
    refinement.pc_screening = 1e-4
    refinement.pc_refined = 2e-4
    refinement.pc_method = "tle_rtn"
    refinement.trigger_source = "screening_auto"

    from backend.app.services.webhook_notifier import notify_pc_escalation

    with (
        patch.dict(os.environ, PAGERDUTY_ENV, clear=False),
        patch("backend.app.db.models.ConjunctionAlert", alert_cls),
        patch("backend.app.db.models.AlertPcRefinement", refine_cls),
    ):
        result = notify_pc_escalation(alert, refinement)
        assert result.sent is True
        body = mock_client.post.call_args.kwargs["json"]
        assert body["payload"]["severity"] == "critical"
        assert body["dedup_key"] == f"cas-alert-{alert_id}"


@patch("backend.app.services.webhook_notifier.httpx.Client")
def test_webhook_test_endpoint_pagerduty_success(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 202
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    with patch.dict(os.environ, PAGERDUTY_ENV, clear=False):
        response = client.post("/api/v1/alerts/webhook/test")
        assert response.status_code == 200
        assert response.json()["sent"] is True


def test_webhook_test_endpoint_pagerduty_without_key_returns_503():
    with patch.dict(
        os.environ,
        {"ALERT_WEBHOOK_FORMAT": "pagerduty", "PAGERDUTY_ROUTING_KEY": ""},
        clear=False,
    ):
        response = client.post("/api/v1/alerts/webhook/test")
        assert response.status_code == 503


@patch("backend.app.services.webhook_notifier.httpx.Client")
def test_health_pagerduty_format(mock_client_cls):
    with patch.dict(os.environ, PAGERDUTY_ENV, clear=False):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["alert_delivery_configured"] is True
        assert data["alert_delivery_format"] == "pagerduty"
