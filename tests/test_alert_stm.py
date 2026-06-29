"""Tests for 6-state alert STM (Phase 10R)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import AlertPcRefinement, Base, ConjunctionAlert, Fleet, Satellite
from backend.app.db.session import get_engine, get_session_factory, reset_engine_for_tests
from backend.app.services import alert_stm_service, pc_refinement_service
from backend.app.services.alert_service import (
    ValidationError,
    ingest_screening_results,
    transition_alert,
)
from backend.app.services.pagerduty_inbound_service import handle_pagerduty_event
from tests.test_alerts_ops import _make_result
from tests.test_auto_pc_refinement import DEMO_SAT

DEBRIS_NORAD = 12345


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
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    from backend.app.main import app

    with TestClient(app) as client:
        yield client
    reset_engine_for_tests()


def _seed_open_alert(db):
    from backend.app.services import fleet_service

    fleet = fleet_service.create_fleet(db, name="STM Fleet")
    sat = fleet_service.add_satellite(db, fleet.id, name=None, norad_id=None, tle=DEMO_SAT)
    opens = ingest_screening_results(
        db,
        run_id=uuid.uuid4(),
        fleet_id=fleet.id,
        results=[_make_result()],
        satellite_by_norad={sat.norad_id: sat.id},
    )
    return opens[0]


def test_stm_matrix_is_6x6():
    matrix = alert_stm_service.stm_matrix()
    assert len(matrix) == 6
    assert all(len(row) == 6 for row in matrix)
    assert alert_stm_service.is_transition_allowed("open", "escalated")
    assert not alert_stm_service.is_transition_allowed("closed", "open")


def test_transition_alert_to_escalated(db_session):
    alert = _seed_open_alert(db_session)
    updated = transition_alert(db_session, alert.id, new_status="escalated", comment="high Pc")
    assert updated.status == "escalated"


def test_transition_closed_to_open_rejected(db_session):
    alert = _seed_open_alert(db_session)
    transition_alert(db_session, alert.id, new_status="acknowledged")
    transition_alert(db_session, alert.id, new_status="closed")
    with pytest.raises(ValidationError):
        transition_alert(db_session, alert.id, new_status="open")


def test_pd_inbound_ack_from_escalated(db_session):
    alert = _seed_open_alert(db_session)
    transition_alert(db_session, alert.id, new_status="escalated")
    result = handle_pagerduty_event(
        db_session,
        {
            "event": {
                "event_type": "incident.acknowledged",
                "data": {"dedup_key": f"cas-alert-{alert.id}"},
            }
        },
    )
    assert result.processed is True
    assert result.status == "acknowledged"


@patch("backend.app.services.webhook_notifier.notify_pc_escalation")
def test_auto_escalate_status_when_enabled(mock_notify, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("PC_ESCALATION_PC_MIN", "1e-5")
    monkeypatch.setenv("ALERT_STM_AUTO_ESCALATE_STATUS", "true")
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    mock_notify.return_value = MagicMock(sent=True, message="ok")

    fleet_id = uuid.uuid4()
    sat_id = uuid.uuid4()
    alert_id = uuid.uuid4()
    db = get_session_factory()()
    try:
        db.add(Fleet(id=fleet_id, name="Auto Esc"))
        db.add(
            Satellite(
                id=sat_id,
                fleet_id=fleet_id,
                name="ISS",
                norad_id=25544,
                tle=DEMO_SAT,
            )
        )
        db.add(
            ConjunctionAlert(
                id=alert_id,
                fleet_id=fleet_id,
                satellite_id=sat_id,
                debris_norad_id=DEBRIS_NORAD,
                debris_name="DEB",
                tca=datetime.now(timezone.utc),
                pc=1e-4,
                miss_distance_km=1.0,
                risk_level="high",
                status="open",
            )
        )
        refinement = AlertPcRefinement(
            alert_id=alert_id,
            pc_screening=1e-4,
            pc_refined=2e-4,
            pc_method="tle_rtn",
            covariance_source="tle_age",
            miss_distance_km=1.0,
            trigger_source="screening_auto",
        )
        db.add(refinement)
        db.commit()
        db.refresh(refinement)

        pc_refinement_service.maybe_escalate_after_refine(db, refinement)
        alert = db.get(ConjunctionAlert, alert_id)
        assert alert is not None
        assert alert.status == "escalated"
    finally:
        db.close()
    reset_engine_for_tests()


def test_ops_state_machine_endpoint(ops_client):
    response = ops_client.get("/api/v1/ops/alerts/state-machine")
    assert response.status_code == 200
    data = response.json()
    assert len(data["statuses"]) == 6
    assert "escalated" in data["statuses"]
    assert len(data["matrix"]) == 6


def test_alert_out_includes_allowed_next_statuses(ops_client, monkeypatch):
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")
    from backend.app.db.session import get_session_factory

    factory = get_session_factory()
    assert factory is not None
    db = factory()
    try:
        alert = _seed_open_alert(db)
        alert_id = str(alert.id)
    finally:
        db.close()

    response = ops_client.get(f"/api/v1/ops/alerts/{alert_id}")
    assert response.status_code == 200
    data = response.json()
    assert "escalated" in data["allowed_next_statuses"]
    assert "acknowledged" in data["allowed_next_statuses"]


def test_reopen_off_acknowledged_to_open_rejected(db_session, monkeypatch):
    monkeypatch.delenv("ALERT_STM_REOPEN_TO_OPEN_ENABLED", raising=False)
    alert = _seed_open_alert(db_session)
    transition_alert(db_session, alert.id, new_status="acknowledged")
    with pytest.raises(ValidationError):
        transition_alert(db_session, alert.id, new_status="open")


@pytest.mark.parametrize("from_status", ["acknowledged", "escalated", "false_positive"])
def test_reopen_on_transition_to_open(db_session, monkeypatch, from_status):
    monkeypatch.setenv("ALERT_STM_REOPEN_TO_OPEN_ENABLED", "true")
    alert = _seed_open_alert(db_session)
    if from_status == "escalated":
        transition_alert(db_session, alert.id, new_status="escalated")
    elif from_status == "acknowledged":
        transition_alert(db_session, alert.id, new_status="acknowledged")
    elif from_status == "false_positive":
        transition_alert(db_session, alert.id, new_status="false_positive")
    updated = transition_alert(db_session, alert.id, new_status="open")
    assert updated.status == "open"


def test_reopen_on_closed_to_open_still_rejected(db_session, monkeypatch):
    monkeypatch.setenv("ALERT_STM_REOPEN_TO_OPEN_ENABLED", "true")
    alert = _seed_open_alert(db_session)
    transition_alert(db_session, alert.id, new_status="acknowledged")
    transition_alert(db_session, alert.id, new_status="closed")
    with pytest.raises(ValidationError):
        transition_alert(db_session, alert.id, new_status="open")


def test_state_machine_reflects_reopen(ops_client, monkeypatch):
    monkeypatch.setenv("ALERT_STM_REOPEN_TO_OPEN_ENABLED", "true")
    response = ops_client.get("/api/v1/ops/alerts/state-machine")
    assert response.status_code == 200
    data = response.json()
    assert data["reopen_to_open_enabled"] is True
    assert "open" in data["allowed_transitions"]["acknowledged"]


def test_allowed_next_includes_open_when_reopen_on(ops_client, monkeypatch):
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "false")
    monkeypatch.setenv("ALERT_STM_REOPEN_TO_OPEN_ENABLED", "true")
    from backend.app.db.session import get_session_factory

    factory = get_session_factory()
    assert factory is not None
    db = factory()
    try:
        alert = _seed_open_alert(db)
        transition_alert(db, alert.id, new_status="acknowledged")
        alert_id = str(alert.id)
    finally:
        db.close()

    response = ops_client.get(f"/api/v1/ops/alerts/{alert_id}")
    assert response.status_code == 200
    assert "open" in response.json()["allowed_next_statuses"]
