"""Tests for Alertmanager automation (Phase 10U)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from backend.app.db.models import Base
from backend.app.db.session import get_engine, get_session_factory, reset_engine_for_tests
from backend.app.services import alertmanager_push_service, alertmanager_silence_service
from backend.app.services.alert_service import ingest_screening_results, transition_alert
from backend.app.tasks.alertmanager_tasks import sync_fleet_alert_breaches
from tests.test_alerts_ops import _make_result
from tests.test_auto_pc_refinement import DEMO_SAT


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
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        yield client
    reset_engine_for_tests()


def _seed_open_alert(db):
    from backend.app.services import fleet_service

    fleet = fleet_service.create_fleet(db, name="Auto Silence Fleet")
    sat = fleet_service.add_satellite(db, fleet.id, name=None, norad_id=None, tle=DEMO_SAT)
    opens = ingest_screening_results(
        db,
        run_id=uuid.uuid4(),
        fleet_id=fleet.id,
        results=[_make_result()],
        satellite_by_norad={sat.norad_id: sat.id},
    )
    return opens[0]


@patch("backend.app.services.alertmanager_silence_service.create_fleet_silence")
def test_auto_silence_off_does_not_create_silence(mock_create, db_session, monkeypatch):
    monkeypatch.delenv("ALERTMANAGER_AUTO_SILENCE_ON_TRIAGE_ENABLED", raising=False)
    alert = _seed_open_alert(db_session)
    transition_alert(db_session, alert.id, new_status="acknowledged")
    mock_create.assert_not_called()


@patch("backend.app.services.alertmanager_silence_service.create_fleet_silence")
def test_auto_silence_on_acknowledged(mock_create, db_session, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_AUTO_SILENCE_ON_TRIAGE_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_SILENCES_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    mock_create.return_value = alertmanager_silence_service.SilenceResult(
        ok=True,
        message="ok",
        silence_id="silence-1",
    )

    alert = _seed_open_alert(db_session)
    transition_alert(db_session, alert.id, new_status="acknowledged")
    mock_create.assert_called_once()
    assert mock_create.call_args.kwargs.get("duration_hours") is not None


@patch("backend.app.services.alertmanager_silence_service.create_fleet_silence")
def test_auto_silence_on_false_positive(mock_create, db_session, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_AUTO_SILENCE_ON_TRIAGE_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_SILENCES_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    mock_create.return_value = alertmanager_silence_service.SilenceResult(
        ok=True,
        message="ok",
        silence_id="silence-2",
    )

    alert = _seed_open_alert(db_session)
    transition_alert(db_session, alert.id, new_status="false_positive")
    mock_create.assert_called_once()


@patch("backend.app.services.alertmanager_silence_service.create_fleet_silence")
def test_auto_silence_not_on_escalated(mock_create, db_session, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_AUTO_SILENCE_ON_TRIAGE_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_SILENCES_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")

    alert = _seed_open_alert(db_session)
    transition_alert(db_session, alert.id, new_status="escalated")
    mock_create.assert_not_called()


@patch("backend.app.services.fleet_metrics_sync_service.collect_and_export_fleet_metrics")
def test_celery_sync_task_calls_metrics_and_breach(mock_collect, monkeypatch):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_PUSH_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_PUSH_CELERY_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)

    result = sync_fleet_alert_breaches()
    assert result["status"] == "ok"
    mock_collect.assert_called_once()
    assert mock_collect.call_args.kwargs["sync_breaches"] is True


@patch("backend.app.services.alertmanager_push_service.sync_breaches")
def test_metrics_skips_sync_when_celery_push_enabled(mock_sync, ops_client, monkeypatch):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_PUSH_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_PUSH_CELERY_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")
    monkeypatch.delenv("ALERTMANAGER_PUSH_REDIS_STATE_ENABLED", raising=False)

    from backend.app.db.session import get_session_factory
    from backend.app.services.fleet_service import add_satellite, create_fleet

    factory = get_session_factory()
    assert factory is not None
    db_sess = factory()
    try:
        fleet = create_fleet(db_sess, name="Metrics Skip Fleet")
        sat = add_satellite(db_sess, fleet.id, name=None, norad_id=None, tle=DEMO_SAT)
        ingest_screening_results(
            db_sess,
            run_id=uuid.uuid4(),
            fleet_id=fleet.id,
            results=[_make_result()],
            satellite_by_norad={sat.norad_id: sat.id},
        )
    finally:
        db_sess.close()

    alertmanager_push_service.reset_breach_state_for_tests()
    response = ops_client.get("/metrics")
    assert response.status_code == 200
    mock_sync.assert_not_called()


@patch("backend.app.services.alertmanager_push_service.sync_breaches")
def test_metrics_syncs_when_celery_and_redis_enabled(mock_sync, ops_client, monkeypatch):
    monkeypatch.setenv("FLEET_ALERT_METRICS_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_PUSH_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_PUSH_CELERY_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_PUSH_REDIS_STATE_ENABLED", "true")
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alertmanager:9093")

    from backend.app.db.session import get_session_factory
    from backend.app.services.fleet_service import add_satellite, create_fleet

    factory = get_session_factory()
    assert factory is not None
    db_sess = factory()
    try:
        fleet = create_fleet(db_sess, name="Metrics Dual Push Fleet")
        sat = add_satellite(db_sess, fleet.id, name=None, norad_id=None, tle=DEMO_SAT)
        ingest_screening_results(
            db_sess,
            run_id=uuid.uuid4(),
            fleet_id=fleet.id,
            results=[_make_result()],
            satellite_by_norad={sat.norad_id: sat.id},
        )
    finally:
        db_sess.close()

    alertmanager_push_service.reset_breach_state_for_tests()
    response = ops_client.get("/metrics")
    assert response.status_code == 200
    mock_sync.assert_called_once()
