"""Tests for per-fleet alert Prometheus metrics (Phase 10Q)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import Base
from backend.app.db.session import get_engine, reset_engine_for_tests
from backend.app.services import fleet_alert_metrics_service
from backend.app.services.alert_service import ingest_screening_results
from backend.app.services.fleet_service import add_satellite, create_fleet
from tests.test_alerts_ops import _make_event, _make_result
from tests.test_fleet_api_slo import _create_fleet_with_key


@pytest.fixture
def db_session(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    reset_engine_for_tests()
    engine = get_engine()
    assert engine is not None
    Base.metadata.create_all(engine)
    from backend.app.db.session import get_session_factory

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


def test_fleet_alert_metrics_disabled_by_default(monkeypatch):
    monkeypatch.delenv("FLEET_ALERT_METRICS_ENABLED", raising=False)
    assert fleet_alert_metrics_service.fleet_alert_metrics_enabled() is False


def _seed_two_open_alerts(db):
    from pathlib import Path

    demo_sat = (Path(__file__).resolve().parents[1] / "samples" / "demo-satellite.tle").read_text(
        encoding="utf-8"
    ).strip()
    fleet = create_fleet(db, name="Alert Metrics Fleet")
    sat = add_satellite(db, fleet.id, name=None, norad_id=None, tle=demo_sat)
    tca1 = datetime.now(timezone.utc)
    ingest_screening_results(
        db,
        run_id=uuid.uuid4(),
        fleet_id=fleet.id,
        results=[_make_result(events=[_make_event(debris_norad=11111, tca=tca1)])],
        satellite_by_norad={sat.norad_id: sat.id},
    )
    ingest_screening_results(
        db,
        run_id=uuid.uuid4(),
        fleet_id=fleet.id,
        results=[_make_result(events=[_make_event(debris_norad=22222, tca=tca1 + timedelta(hours=30))])],
        satellite_by_norad={sat.norad_id: sat.id},
    )
    return fleet


def test_prometheus_exports_fleet_alert_metrics(ops_client, monkeypatch):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("FLEET_ALERT_OPEN_THRESHOLD", "1")
    from backend.app.db.session import get_session_factory

    factory = get_session_factory()
    assert factory is not None
    db_sess = factory()
    try:
        fleet = _seed_two_open_alerts(db_sess)
        fleet_id = str(fleet.id)
    finally:
        db_sess.close()

    response = ops_client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "cas_fleet_alerts_total" in body
    assert f'fleet_id="{fleet_id}"' in body
    assert 'status="open"' in body
    assert "cas_fleet_open_alerts_breach" in body


def test_fleet_alert_rules_endpoint_yaml(ops_client, monkeypatch):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    fleet_id, _fleet_key = _create_fleet_with_key(ops_client, monkeypatch, "Rules Fleet")

    from backend.app.db.session import get_session_factory
    from pathlib import Path

    factory = get_session_factory()
    assert factory is not None
    db_sess = factory()
    try:
        demo_sat = (Path(__file__).resolve().parents[1] / "samples" / "demo-satellite.tle").read_text(
            encoding="utf-8"
        ).strip()
        sat = add_satellite(db_sess, uuid.UUID(fleet_id), name=None, norad_id=None, tle=demo_sat)
        ingest_screening_results(
            db_sess,
            run_id=uuid.uuid4(),
            fleet_id=uuid.UUID(fleet_id),
            results=[_make_result()],
            satellite_by_norad={sat.norad_id: sat.id},
        )
    finally:
        db_sess.close()

    response = ops_client.get(
        f"/api/v1/ops/prometheus/fleet-alert-rules?fleet_id={fleet_id}",
        headers={"X-API-Key": "admin-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "yaml"
    assert data["fleet_id"] == fleet_id
    assert "cas_fleet_alerts_total" in data["content"]
    assert fleet_id in data["content"]
    assert "CASFleetOpenAlertsHigh" in data["content"]
    assert "CASFleetHighRiskOpenAlerts" in data["content"]


def test_fleet_alert_rules_disabled_returns_503(ops_client, monkeypatch):
    monkeypatch.delenv("FLEET_ALERT_METRICS_ENABLED", raising=False)
    response = ops_client.get("/api/v1/ops/prometheus/fleet-alert-rules")
    assert response.status_code == 503


def test_fleet_scoped_key_cannot_access_other_fleet_rules(ops_client, monkeypatch):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    fleet_a, key_a = _create_fleet_with_key(ops_client, monkeypatch, "Fleet A Rules")
    fleet_b, _ = _create_fleet_with_key(ops_client, monkeypatch, "Fleet B Rules")

    response = ops_client.get(
        f"/api/v1/ops/prometheus/fleet-alert-rules?fleet_id={fleet_b}",
        headers={"X-API-Key": key_a},
    )
    assert response.status_code == 403


def test_render_fleet_alert_rules_json():
    rules = fleet_alert_metrics_service.render_fleet_alert_rules(
        uuid.uuid4(),
        "Test Fleet",
    )
    content = fleet_alert_metrics_service.render_fleet_alert_rules_json(rules)
    assert "cas-fleet-alerts" in content
    assert "CASFleetOpenAlertsHigh" in content
    assert "CASFleetHighRiskOpenAlerts" in content
    assert "cas_fleet_alerts_total" in content


def test_render_fleet_alert_rules_breaching_only():
    fleet_id = uuid.uuid4()
    rules = fleet_alert_metrics_service.render_fleet_alert_rules(
        fleet_id,
        "Gauge Fleet",
        breaching_only=True,
    )
    assert "cas_fleet_open_alerts_breach" in rules[0]["expr"]
    assert "cas_fleet_high_risk_open_breach" in rules[1]["expr"]
    assert "cas_fleet_alerts_total" not in rules[0]["expr"]


def test_fleet_alert_rules_breaching_only_api(ops_client, monkeypatch):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")

    fleet_id, _ = _create_fleet_with_key(ops_client, monkeypatch, "Gauge Rules Fleet")
    response = ops_client.get(
        f"/api/v1/ops/prometheus/fleet-alert-rules?fleet_id={fleet_id}&breaching_only=true",
        headers={"X-API-Key": "admin-secret"},
    )
    assert response.status_code == 200
    assert "cas_fleet_open_alerts_breach" in response.json()["content"]
    assert "cas_fleet_high_risk_open_breach" in response.json()["content"]


def test_fleet_alert_rules_breaching_fleets_only(ops_client, monkeypatch):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")

    from backend.app.services import breach_state_store

    fleet_a, _ = _create_fleet_with_key(ops_client, monkeypatch, "Breaching Rules Fleet")
    fleet_b, _ = _create_fleet_with_key(ops_client, monkeypatch, "OK Rules Fleet")
    breach_state_store.set_breach_state(fleet_a, "CASFleetOpenAlertsHigh", True)

    response = ops_client.get(
        "/api/v1/ops/prometheus/fleet-alert-rules?breaching_fleets_only=true",
        headers={"X-API-Key": "admin-secret"},
    )
    assert response.status_code == 200
    content = response.json()["content"]
    assert fleet_a in content
    assert fleet_b not in content
    assert content.count("alert: CASFleetOpenAlertsHigh") == 1


def test_fleet_alert_rules_apply_writes_file(ops_client, monkeypatch, tmp_path):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")

    output = tmp_path / "fleet-rules.yaml"
    monkeypatch.setenv("PROMETHEUS_FLEET_RULES_OUTPUT_PATH", str(output))

    fleet_id, _ = _create_fleet_with_key(ops_client, monkeypatch, "Apply Rules Fleet")
    response = ops_client.post(
        f"/api/v1/ops/prometheus/fleet-alert-rules/apply?fleet_id={fleet_id}",
        headers={"X-API-Key": "admin-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["applied"] is True
    assert data["path"] == str(output)
    assert data["reloaded"] is False
    assert output.exists()
    assert "CASFleetOpenAlertsHigh" in output.read_text(encoding="utf-8")


def test_prometheus_reload_after_apply(ops_client, monkeypatch, tmp_path):
    from unittest.mock import MagicMock, patch

    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")

    output = tmp_path / "fleet-rules.yaml"
    monkeypatch.setenv("PROMETHEUS_FLEET_RULES_OUTPUT_PATH", str(output))
    monkeypatch.setenv("PROMETHEUS_RELOAD_URL", "http://prometheus:9090/-/reload")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False

    fleet_id, _ = _create_fleet_with_key(ops_client, monkeypatch, "Reload Rules Fleet")
    with patch(
        "backend.app.services.fleet_alert_rules_apply_service.httpx.Client",
        return_value=mock_client,
    ):
        response = ops_client.post(
            f"/api/v1/ops/prometheus/fleet-alert-rules/apply?fleet_id={fleet_id}",
            headers={"X-API-Key": "admin-secret"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["applied"] is True
    assert data["reloaded"] is True
    mock_client.post.assert_called_once()


def test_prometheus_reload_skipped_when_url_unset(ops_client, monkeypatch, tmp_path):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")
    monkeypatch.delenv("PROMETHEUS_RELOAD_URL", raising=False)

    output = tmp_path / "fleet-rules.yaml"
    monkeypatch.setenv("PROMETHEUS_FLEET_RULES_OUTPUT_PATH", str(output))

    fleet_id, _ = _create_fleet_with_key(ops_client, monkeypatch, "No Reload Fleet")
    response = ops_client.post(
        f"/api/v1/ops/prometheus/fleet-alert-rules/apply?fleet_id={fleet_id}",
        headers={"X-API-Key": "admin-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["applied"] is True
    assert data["reloaded"] is False
    assert "PROMETHEUS_RELOAD_URL" in (data["reload_message"] or "")


def test_prometheus_reload_retries_on_failure(ops_client, monkeypatch, tmp_path):
    from unittest.mock import MagicMock, patch

    import httpx

    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")
    monkeypatch.setenv("PROMETHEUS_RELOAD_MAX_RETRIES", "3")

    output = tmp_path / "fleet-rules.yaml"
    monkeypatch.setenv("PROMETHEUS_FLEET_RULES_OUTPUT_PATH", str(output))
    monkeypatch.setenv("PROMETHEUS_RELOAD_URL", "http://prometheus:9090/-/reload")

    mock_client = MagicMock()
    fail_response = MagicMock()
    fail_response.raise_for_status.side_effect = httpx.HTTPError("connection failed")
    ok_response = MagicMock()
    mock_client.post.side_effect = [fail_response, fail_response, ok_response]
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False

    fleet_id, _ = _create_fleet_with_key(ops_client, monkeypatch, "Retry Reload Fleet")
    with patch(
        "backend.app.services.fleet_alert_rules_apply_service.httpx.Client",
        return_value=mock_client,
    ):
        response = ops_client.post(
            f"/api/v1/ops/prometheus/fleet-alert-rules/apply?fleet_id={fleet_id}",
            headers={"X-API-Key": "admin-secret"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["applied"] is True
    assert data["reloaded"] is True
    assert data["reload_queued"] is False
    assert mock_client.post.call_count == 3


def test_prometheus_reload_celery_fallback_on_exhausted_retries(ops_client, monkeypatch, tmp_path):
    from unittest.mock import MagicMock, patch

    import httpx

    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")
    monkeypatch.setenv("PROMETHEUS_RELOAD_MAX_RETRIES", "2")
    monkeypatch.setenv("PROMETHEUS_RELOAD_CELERY_FALLBACK", "true")

    output = tmp_path / "fleet-rules.yaml"
    monkeypatch.setenv("PROMETHEUS_FLEET_RULES_OUTPUT_PATH", str(output))
    monkeypatch.setenv("PROMETHEUS_RELOAD_URL", "http://prometheus:9090/-/reload")

    mock_client = MagicMock()
    fail_response = MagicMock()
    fail_response.raise_for_status.side_effect = httpx.HTTPError("connection failed")
    mock_client.post.return_value = fail_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False

    mock_delay = MagicMock()
    mock_delay.return_value = MagicMock(id="celery-reload-task-123")
    fleet_id, _ = _create_fleet_with_key(ops_client, monkeypatch, "Celery Reload Fleet")
    with patch(
        "backend.app.services.fleet_alert_rules_apply_service.httpx.Client",
        return_value=mock_client,
    ), patch(
        "backend.app.tasks.alertmanager_tasks.prometheus_reload_task.delay",
        mock_delay,
    ):
        response = ops_client.post(
            f"/api/v1/ops/prometheus/fleet-alert-rules/apply?fleet_id={fleet_id}",
            headers={"X-API-Key": "admin-secret"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["applied"] is True
    assert data["reloaded"] is False
    assert data["reload_queued"] is True
    assert data["reload_task_id"] == "celery-reload-task-123"
    assert mock_client.post.call_count == 2
    mock_delay.assert_called_once()


def test_apply_returns_reload_task_id_on_celery_fallback(ops_client, monkeypatch, tmp_path):
    from unittest.mock import MagicMock, patch

    import httpx

    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")
    monkeypatch.setenv("PROMETHEUS_RELOAD_CELERY_FALLBACK", "true")

    output = tmp_path / "fleet-rules.yaml"
    monkeypatch.setenv("PROMETHEUS_FLEET_RULES_OUTPUT_PATH", str(output))
    monkeypatch.setenv("PROMETHEUS_RELOAD_URL", "http://prometheus:9090/-/reload")

    mock_client = MagicMock()
    fail_response = MagicMock()
    fail_response.raise_for_status.side_effect = httpx.HTTPError("connection failed")
    mock_client.post.return_value = fail_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False

    mock_delay = MagicMock()
    mock_delay.return_value = MagicMock(id="queued-task-456")

    fleet_id, _ = _create_fleet_with_key(ops_client, monkeypatch, "Task Id Fleet")
    with patch(
        "backend.app.services.fleet_alert_rules_apply_service.httpx.Client",
        return_value=mock_client,
    ), patch(
        "backend.app.tasks.alertmanager_tasks.prometheus_reload_task.delay",
        mock_delay,
    ):
        response = ops_client.post(
            f"/api/v1/ops/prometheus/fleet-alert-rules/apply?fleet_id={fleet_id}",
            headers={"X-API-Key": "admin-secret"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["reload_task_id"] == "queued-task-456"


def test_prometheus_reload_task_status_eager_success(ops_client, monkeypatch):
    from unittest.mock import MagicMock, patch

    from backend.app.services import fleet_alert_rules_apply_service
    from backend.app.tasks.celery_app import configure_celery_eager

    fleet_alert_rules_apply_service.clear_reload_tasks_for_tests()
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")
    monkeypatch.setenv("PROMETHEUS_RELOAD_URL", "http://prometheus:9090/-/reload")
    configure_celery_eager()

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False

    with patch(
        "backend.app.services.fleet_alert_rules_apply_service.httpx.Client",
        return_value=mock_client,
    ):
        task_id = fleet_alert_rules_apply_service.queue_prometheus_reload()
    assert task_id

    response = ops_client.get(
        f"/api/v1/ops/prometheus/reload/tasks/{task_id}",
        headers={"X-API-Key": "admin-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["state"] == "SUCCESS"
    assert data["reloaded"] is True


def test_prometheus_reload_task_status_not_found(ops_client, monkeypatch):
    from backend.app.services import fleet_alert_rules_apply_service

    fleet_alert_rules_apply_service.clear_reload_tasks_for_tests()
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")

    response = ops_client.get(
        "/api/v1/ops/prometheus/reload/tasks/not-a-known-task-id",
        headers={"X-API-Key": "admin-secret"},
    )
    assert response.status_code == 404


def test_prometheus_reload_task_forbidden_for_fleet_key(ops_client, monkeypatch):
    from backend.app.services import fleet_alert_rules_apply_service

    fleet_alert_rules_apply_service.clear_reload_tasks_for_tests()
    task_id = "known-reload-task-for-auth-test"
    fleet_alert_rules_apply_service._enqueued_reload_task_ids.add(task_id)
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")

    _, plain = _create_fleet_with_key(ops_client, monkeypatch, "Reload Poll Fleet")
    response = ops_client.get(
        f"/api/v1/ops/prometheus/reload/tasks/{task_id}",
        headers={"X-API-Key": plain},
    )
    assert response.status_code == 403


def test_prometheus_reload_manual_endpoint_returns_task_id(ops_client, monkeypatch):
    from unittest.mock import MagicMock, patch

    from backend.app.services import fleet_alert_rules_apply_service

    fleet_alert_rules_apply_service.clear_reload_tasks_for_tests()
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")
    monkeypatch.setenv("PROMETHEUS_RELOAD_URL", "http://prometheus:9090/-/reload")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False

    with patch(
        "backend.app.services.fleet_alert_rules_apply_service.httpx.Client",
        return_value=mock_client,
    ):
        response = ops_client.post(
            "/api/v1/ops/prometheus/reload",
            headers={"X-API-Key": "admin-secret"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["reloaded"] is True
    assert data["reload_queued"] is False


def test_prometheus_reload_history_lists_enqueued_task(ops_client, monkeypatch):
    from unittest.mock import MagicMock, patch

    from backend.app.services import fleet_alert_rules_apply_service

    fleet_alert_rules_apply_service.clear_reload_tasks_for_tests()
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")

    mock_delay = MagicMock()
    mock_delay.id = "history-task-001"
    with patch(
        "backend.app.tasks.alertmanager_tasks.prometheus_reload_task.delay",
        return_value=mock_delay,
    ):
        task_id = fleet_alert_rules_apply_service.queue_prometheus_reload()
    assert task_id == "history-task-001"

    response = ops_client.get(
        "/api/v1/ops/prometheus/reload/history",
        headers={"X-API-Key": "admin-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(item["task_id"] == task_id for item in data["items"])


def test_prometheus_reload_history_records_sync_reload(ops_client, monkeypatch):
    from unittest.mock import MagicMock, patch

    from backend.app.services import fleet_alert_rules_apply_service

    fleet_alert_rules_apply_service.clear_reload_tasks_for_tests()
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")
    monkeypatch.setenv("PROMETHEUS_RELOAD_URL", "http://prometheus:9090/-/reload")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False

    with patch(
        "backend.app.services.fleet_alert_rules_apply_service.httpx.Client",
        return_value=mock_client,
    ):
        response = ops_client.post(
            "/api/v1/ops/prometheus/reload",
            headers={"X-API-Key": "admin-secret"},
        )
    assert response.status_code == 200

    history = ops_client.get(
        "/api/v1/ops/prometheus/reload/history",
        headers={"X-API-Key": "admin-secret"},
    )
    assert history.status_code == 200
    items = history.json()["items"]
    assert len(items) >= 1
    assert items[0]["source"] == "sync"
    assert items[0]["task_id"] is None
    assert items[0]["reloaded"] is True
    assert items[0]["state"] == "SUCCESS"


def test_prometheus_reload_history_respects_limit(ops_client, monkeypatch):
    from backend.app.services import fleet_alert_rules_apply_service

    fleet_alert_rules_apply_service.clear_reload_tasks_for_tests()
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")
    monkeypatch.setenv("PROMETHEUS_RELOAD_HISTORY_SIZE", "2")

    for index in range(3):
        fleet_alert_rules_apply_service.record_sync_prometheus_reload(
            reloaded=True,
            message=f"sync reload {index}",
        )

    response = ops_client.get(
        "/api/v1/ops/prometheus/reload/history?limit=1",
        headers={"X-API-Key": "admin-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["message"] == "sync reload 2"


def test_prometheus_reload_history_forbidden_for_fleet_key(ops_client, monkeypatch):
    from backend.app.services import fleet_alert_rules_apply_service

    fleet_alert_rules_apply_service.clear_reload_tasks_for_tests()
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")

    _, plain = _create_fleet_with_key(ops_client, monkeypatch, "Reload History Fleet")
    response = ops_client.get(
        "/api/v1/ops/prometheus/reload/history",
        headers={"X-API-Key": plain},
    )
    assert response.status_code == 403


def test_prometheus_reload_history_empty(ops_client, monkeypatch):
    from backend.app.services import fleet_alert_rules_apply_service

    fleet_alert_rules_apply_service.clear_reload_tasks_for_tests()
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")

    response = ops_client.get(
        "/api/v1/ops/prometheus/reload/history",
        headers={"X-API-Key": "admin-secret"},
    )
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_fleet_alert_rules_apply_no_path_returns_not_applied(ops_client, monkeypatch):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")
    monkeypatch.delenv("PROMETHEUS_FLEET_RULES_OUTPUT_PATH", raising=False)

    fleet_id, _ = _create_fleet_with_key(ops_client, monkeypatch, "Apply No Path Fleet")
    response = ops_client.post(
        f"/api/v1/ops/prometheus/fleet-alert-rules/apply?fleet_id={fleet_id}",
        headers={"X-API-Key": "admin-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["applied"] is False
    assert data["path"] is None
    assert data["reloaded"] is False
    assert "PROMETHEUS_FLEET_RULES_OUTPUT_PATH" in data["message"]


def test_collect_fleet_risk_counts_high_open(db_session):
    from pathlib import Path

    demo_sat = (Path(__file__).resolve().parents[1] / "samples" / "demo-satellite.tle").read_text(
        encoding="utf-8"
    ).strip()
    fleet = create_fleet(db_session, name="Risk Metrics Fleet")
    sat = add_satellite(db_session, fleet.id, name=None, norad_id=None, tle=demo_sat)
    ingest_screening_results(
        db_session,
        run_id=uuid.uuid4(),
        fleet_id=fleet.id,
        results=[_make_result(events=[_make_event(risk="high")])],
        satellite_by_norad={sat.norad_id: sat.id},
    )
    risk_counts = fleet_alert_metrics_service.collect_fleet_risk_counts(db_session)
    assert risk_counts[fleet.id]["high"]["open"] == 1


def test_prometheus_exports_risk_metrics(ops_client, monkeypatch):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("FLEET_ALERT_HIGH_RISK_THRESHOLD", "1")
    from backend.app.db.session import get_session_factory
    from pathlib import Path

    factory = get_session_factory()
    assert factory is not None
    db_sess = factory()
    try:
        demo_sat = (Path(__file__).resolve().parents[1] / "samples" / "demo-satellite.tle").read_text(
            encoding="utf-8"
        ).strip()
        fleet = create_fleet(db_sess, name="Risk Prom Fleet")
        sat = add_satellite(db_sess, fleet.id, name=None, norad_id=None, tle=demo_sat)
        ingest_screening_results(
            db_sess,
            run_id=uuid.uuid4(),
            fleet_id=fleet.id,
            results=[_make_result(events=[_make_event(risk="high")])],
            satellite_by_norad={sat.norad_id: sat.id},
        )
        fleet_id = str(fleet.id)
    finally:
        db_sess.close()

    response = ops_client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "cas_fleet_alerts_by_risk_total" in body
    assert 'risk_level="high"' in body
    assert "cas_fleet_high_risk_open_breach" in body
    assert f'fleet_id="{fleet_id}"' in body


def test_fleet_summary_includes_open_risk_counts(ops_client, monkeypatch):
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")
    from backend.app.db.session import get_session_factory
    from pathlib import Path

    factory = get_session_factory()
    assert factory is not None
    db_sess = factory()
    try:
        demo_sat = (Path(__file__).resolve().parents[1] / "samples" / "demo-satellite.tle").read_text(
            encoding="utf-8"
        ).strip()
        fleet = create_fleet(db_sess, name="Summary Risk Fleet")
        sat = add_satellite(db_sess, fleet.id, name=None, norad_id=None, tle=demo_sat)
        ingest_screening_results(
            db_sess,
            run_id=uuid.uuid4(),
            fleet_id=fleet.id,
            results=[_make_result(events=[_make_event(risk="high")])],
            satellite_by_norad={sat.norad_id: sat.id},
        )
        fleet_id = str(fleet.id)
    finally:
        db_sess.close()

    response = ops_client.get(f"/api/v1/ops/fleets/{fleet_id}/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["open_high_count"] == 1
    assert data["open_medium_count"] == 0
    assert data["open_low_count"] == 0
