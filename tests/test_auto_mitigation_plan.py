"""Tests for auto mitigation plan transition (Phase 10G)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import AlertMitigationPreview, AuditLog, Base, ConjunctionAlert
from backend.app.db.session import get_engine, get_session_factory, reset_engine_for_tests
from backend.app.services import mitigation_service
from backend.app.services.analysis import ConjunctionAnalysisResult
from backend.app.services.conjunction import ConjunctionEvent
from backend.app.services.alert_service import ingest_screening_results
from backend.app.services.tle_parser import parse_tle

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
DEMO_SAT = (SAMPLES / "demo-satellite.tle").read_text(encoding="utf-8").strip()
DEMO_DEB = (SAMPLES / "demo-debris.tle").read_text(encoding="utf-8").strip()
DEBRIS_NORAD = parse_tle(DEMO_DEB).norad_id


def _make_event(
    *,
    debris_norad: int = DEBRIS_NORAD,
    tca: datetime | None = None,
    pc: float = 1e-4,
    risk: str = "high",
) -> ConjunctionEvent:
    return ConjunctionEvent(
        debris_norad_id=debris_norad,
        debris_name="COSMOS 2251 DEB",
        debris_tle=DEMO_DEB,
        tca=tca or datetime.now(timezone.utc),
        miss_distance_km=1.0,
        relative_velocity_kms=7.0,
        risk_level=risk,
        pc=pc,
    )


def _make_result(norad_id: int = 25544, events: list[ConjunctionEvent] | None = None):
    from dataclasses import replace

    parsed = parse_tle(DEMO_SAT)
    if norad_id != parsed.norad_id:
        parsed = replace(parsed, norad_id=norad_id)
    return ConjunctionAnalysisResult(
        satellite=parsed,
        start=datetime.now(timezone.utc),
        end=datetime.now(timezone.utc),
        threshold_km=50.0,
        events=events or [_make_event()],
        debris_catalog_count=1,
        debris_candidates_count=1,
        altitude_prefilter_applied=False,
        computation_time_ms=10,
        tle_cache_stale=False,
        tle_provider="test",
    )


@pytest.fixture
def db_session(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    factory = get_session_factory()
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


def _seed_alert_with_preview(
    db,
    *,
    status: str = "acknowledged",
    improving: bool = True,
    trigger_source: str = "screening_auto",
) -> tuple[uuid.UUID, AlertMitigationPreview]:
    from backend.app.db.models import Fleet, Satellite

    fleet_id = uuid.uuid4()
    sat_id = uuid.uuid4()
    alert_id = uuid.uuid4()
    db.add(Fleet(id=fleet_id, name="Auto Plan Fleet"))
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
            status=status,
        )
    )
    preview = AlertMitigationPreview(
        alert_id=alert_id,
        direction="prograde",
        delta_v_ms=0.01,
        before_tca=datetime.now(timezone.utc),
        before_miss_distance_km=1.0,
        after_tca=datetime.now(timezone.utc),
        after_miss_distance_km=2.0 if improving else 0.5,
        trigger_source=trigger_source,
    )
    db.add(preview)
    db.commit()
    db.refresh(preview)
    return alert_id, preview


@patch("backend.app.services.webhook_notifier.notify_mitigation_plan_auto")
def test_maybe_auto_plan_acknowledged_improving(mock_notify, db_session, monkeypatch):
    monkeypatch.setenv("AUTO_MITIGATION_PLAN_ENABLED", "true")
    mock_notify.return_value = MagicMock(sent=True)

    alert_id, preview = _seed_alert_with_preview(db_session, status="acknowledged")
    result = mitigation_service.maybe_auto_mitigation_plan(db_session, alert_id, preview)

    assert result is not None
    assert result.status == "mitigation_planned"
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "alert.mitigation_plan_auto")
        .one()
    )
    assert audit.resource_id == alert_id
    assert audit.detail["preview_id"] == str(preview.id)
    mock_notify.assert_called_once()


@patch("backend.app.services.webhook_notifier.notify_mitigation_plan_auto")
def test_maybe_auto_plan_open_with_auto_ack(mock_notify, db_session, monkeypatch):
    monkeypatch.setenv("AUTO_MITIGATION_PLAN_ENABLED", "true")
    monkeypatch.setenv("AUTO_ACK_BEFORE_MITIGATION_PLAN", "true")
    mock_notify.return_value = MagicMock(sent=True)

    alert_id, preview = _seed_alert_with_preview(db_session, status="open")
    result = mitigation_service.maybe_auto_mitigation_plan(db_session, alert_id, preview)

    assert result is not None
    assert result.status == "mitigation_planned"
    auto_audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "alert.mitigation_plan_auto")
        .one()
    )
    assert auto_audit.detail["auto_ack"] is True
    ack_audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "alert.transition")
        .order_by(AuditLog.created_at)
        .first()
    )
    assert ack_audit is not None


def test_maybe_auto_plan_open_without_auto_ack_skips(db_session, monkeypatch):
    monkeypatch.setenv("AUTO_MITIGATION_PLAN_ENABLED", "true")
    monkeypatch.setenv("AUTO_ACK_BEFORE_MITIGATION_PLAN", "false")

    alert_id, preview = _seed_alert_with_preview(db_session, status="open")
    result = mitigation_service.maybe_auto_mitigation_plan(db_session, alert_id, preview)

    assert result is None
    assert (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "alert.mitigation_plan_auto")
        .count()
        == 0
    )


def test_maybe_auto_plan_disabled_skips(db_session, monkeypatch):
    monkeypatch.setenv("AUTO_MITIGATION_PLAN_ENABLED", "false")

    alert_id, preview = _seed_alert_with_preview(db_session, status="acknowledged")
    result = mitigation_service.maybe_auto_mitigation_plan(db_session, alert_id, preview)

    assert result is None


def test_maybe_auto_plan_non_improving_skips(db_session, monkeypatch):
    monkeypatch.setenv("AUTO_MITIGATION_PLAN_ENABLED", "true")

    alert_id, preview = _seed_alert_with_preview(
        db_session, status="acknowledged", improving=False
    )
    result = mitigation_service.maybe_auto_mitigation_plan(db_session, alert_id, preview)

    assert result is None


@patch("backend.app.services.webhook_notifier.notify_mitigation_plan_auto")
def test_notify_mitigation_plan_auto_called(mock_notify, db_session, monkeypatch):
    monkeypatch.setenv("AUTO_MITIGATION_PLAN_ENABLED", "true")
    mock_notify.return_value = MagicMock(sent=True, message="ok")

    alert_id, preview = _seed_alert_with_preview(db_session, status="acknowledged")
    mitigation_service.maybe_auto_mitigation_plan(db_session, alert_id, preview)

    mock_notify.assert_called_once()
    call_alert, call_preview = mock_notify.call_args[0]
    assert call_alert.id == alert_id
    assert call_preview.id == preview.id


@patch("backend.app.services.webhook_notifier.notify_mitigation_plan_auto")
@patch("backend.app.tasks.mitigation_tasks.mitigation_service.maybe_notify_mitigation_best")
@patch("backend.app.tasks.mitigation_tasks.mitigation_service.run_alert_mitigation_sweep")
def test_mitigation_sweep_task_auto_plans(
    mock_sweep, mock_notify_best, mock_notify_plan, monkeypatch
):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("AUTO_MITIGATION_PLAN_ENABLED", "true")
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)

    mock_notify_best.return_value = True
    mock_notify_plan.return_value = MagicMock(sent=True)

    db = get_session_factory()()
    try:
        alert_id, preview = _seed_alert_with_preview(db, status="acknowledged")
    finally:
        db.close()
    mock_sweep.return_value = ([preview], preview)

    from backend.app.tasks.mitigation_tasks import mitigation_sweep_task

    result = mitigation_sweep_task(str(alert_id))
    assert result["auto_planned"] is True
    assert result["new_status"] == "mitigation_planned"

    db = get_session_factory()()
    try:
        alert = db.get(ConjunctionAlert, alert_id)
        assert alert.status == "mitigation_planned"
        assert (
            db.query(AuditLog)
            .filter(AuditLog.action == "alert.mitigation_plan_auto")
            .count()
            == 1
        )
    finally:
        db.close()
    reset_engine_for_tests()


@patch("backend.app.services.webhook_notifier.notify_mitigation_plan_auto")
def test_ops_auto_mitigation_planned_flag(mock_notify, ops_client, monkeypatch):
    monkeypatch.setenv("AUTO_MITIGATION_PLAN_ENABLED", "true")
    mock_notify.return_value = MagicMock(sent=True)

    fleet = ops_client.post("/api/v1/fleets", json={"name": "Ops Auto Plan"}).json()
    sat = ops_client.post(
        f"/api/v1/fleets/{fleet['id']}/satellites", json={"tle": DEMO_SAT}
    ).json()
    db = get_session_factory()()
    try:
        ingest_screening_results(
            db,
            run_id=uuid.uuid4(),
            fleet_id=uuid.UUID(fleet["id"]),
            results=[_make_result(norad_id=sat["norad_id"])],
            satellite_by_norad={sat["norad_id"]: uuid.UUID(sat["id"])},
        )
    finally:
        db.close()

    alert_id = ops_client.get(
        f"/api/v1/ops/alerts?fleet_id={fleet['id']}"
    ).json()["items"][0]["id"]
    ops_client.patch(
        f"/api/v1/ops/alerts/{alert_id}",
        json={"status": "acknowledged"},
    )

    db = get_session_factory()()
    try:
        alert_id_uuid = uuid.UUID(alert_id)
        preview = AlertMitigationPreview(
            alert_id=alert_id_uuid,
            direction="prograde",
            delta_v_ms=0.01,
            before_tca=datetime.now(timezone.utc),
            before_miss_distance_km=1.0,
            after_tca=datetime.now(timezone.utc),
            after_miss_distance_km=2.0,
            trigger_source="screening_auto",
        )
        db.add(preview)
        db.commit()
        db.refresh(preview)
        mitigation_service.maybe_auto_mitigation_plan(db, alert_id_uuid, preview)
    finally:
        db.close()

    detail = ops_client.get(f"/api/v1/ops/alerts/{alert_id}").json()
    assert detail["status"] == "mitigation_planned"
    assert detail["auto_mitigation_planned"] is True
