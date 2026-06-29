"""Tests for screening auto mitigation sweep (Phase 10F)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import AlertMitigationPreview, AuditLog, Base, ConjunctionAlert
from backend.app.db.session import get_engine, get_session_factory, reset_engine_for_tests
from backend.app.services.alert_service import ingest_screening_results
from backend.app.services.analysis import ConjunctionAnalysisResult
from backend.app.services.conjunction import ConjunctionEvent
from backend.app.services import mitigation_service
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
def ops_client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    from backend.app.main import app

    with TestClient(app) as client:
        yield client
    reset_engine_for_tests()


def _seed_alert(ops_client: TestClient) -> str:
    fleet = ops_client.post("/api/v1/fleets", json={"name": "Auto Mit Fleet"}).json()
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
    return ops_client.get(f"/api/v1/ops/alerts?fleet_id={fleet['id']}").json()["items"][0]["id"]


def test_should_auto_mitigation_sweep_respects_env(monkeypatch):
    monkeypatch.setenv("AUTO_MITIGATION_SWEEP_ENABLED", "false")
    assert mitigation_service.should_auto_mitigation_sweep(
        escalated=True, pc_refined=1e-4
    ) is False

    monkeypatch.setenv("AUTO_MITIGATION_SWEEP_ENABLED", "true")
    monkeypatch.setenv("AUTO_MITIGATION_SWEEP_ON_ESCALATION_ONLY", "true")
    assert mitigation_service.should_auto_mitigation_sweep(
        escalated=True, pc_refined=1e-4
    ) is True
    assert mitigation_service.should_auto_mitigation_sweep(
        escalated=False, pc_refined=1e-4
    ) is False

    monkeypatch.setenv("AUTO_MITIGATION_SWEEP_ON_ESCALATION_ONLY", "false")
    monkeypatch.setenv("AUTO_MITIGATION_SWEEP_PC_MIN", "1e-5")
    assert mitigation_service.should_auto_mitigation_sweep(
        escalated=False, pc_refined=1e-4
    ) is True
    assert mitigation_service.should_auto_mitigation_sweep(
        escalated=False, pc_refined=1e-8
    ) is False


@patch("backend.app.tasks.mitigation_tasks.mitigation_sweep_task")
def test_enqueue_auto_mitigation_sweep(mock_task, monkeypatch):
    monkeypatch.setenv("AUTO_MITIGATION_SWEEP_ENABLED", "true")
    monkeypatch.setenv("AUTO_MITIGATION_SWEEP_ON_ESCALATION_ONLY", "true")

    aid = uuid.uuid4()
    assert mitigation_service.enqueue_auto_mitigation_sweep(
        aid, escalated=True, pc_refined=1e-4
    ) is True
    mock_task.delay.assert_called_once_with(str(aid))

    mock_task.delay.reset_mock()
    assert mitigation_service.enqueue_auto_mitigation_sweep(
        aid, escalated=False, pc_refined=1e-4
    ) is False
    mock_task.delay.assert_not_called()


@patch("backend.app.tasks.mitigation_tasks.mitigation_sweep_task")
def test_enqueue_disabled(mock_task, monkeypatch):
    monkeypatch.setenv("AUTO_MITIGATION_SWEEP_ENABLED", "false")
    assert mitigation_service.enqueue_auto_mitigation_sweep(
        uuid.uuid4(), escalated=True, pc_refined=1e-3
    ) is False
    mock_task.delay.assert_not_called()


@patch("backend.app.services.mitigation_service.find_tle_by_norad_id")
@patch("backend.app.services.mitigation_service.maybe_notify_mitigation_best")
def test_mitigation_sweep_task_screening_auto(mock_notify, mock_find, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)

    mock_find.return_value = parse_tle(DEMO_DEB)
    mock_notify.return_value = True

    fleet_id = uuid.uuid4()
    sat_id = uuid.uuid4()
    alert_id = uuid.uuid4()
    db = get_session_factory()()
    try:
        from backend.app.db.models import Fleet, Satellite

        db.add(Fleet(id=fleet_id, name="Task Fleet"))
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
        db.commit()
    finally:
        db.close()

    from backend.app.tasks.mitigation_tasks import mitigation_sweep_task

    result = mitigation_sweep_task(str(alert_id))
    assert result["trigger_source"] == "screening_auto"
    assert result["trial_count"] >= 1
    assert result["best_preview_id"] is not None

    db = get_session_factory()()
    try:
        rows = db.query(AlertMitigationPreview).all()
        assert len(rows) >= 1
        assert all(r.trigger_source == "screening_auto" for r in rows)
        audit = (
            db.query(AuditLog)
            .filter(AuditLog.action == "alert.mitigation_sweep_auto")
            .one()
        )
        assert audit.resource_id == alert_id
    finally:
        db.close()
    reset_engine_for_tests()


@patch("backend.app.services.webhook_notifier.notify_mitigation_best")
def test_maybe_notify_mitigation_best(mock_notify, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)

    mock_notify.return_value = MagicMock(sent=True, message="ok")

    fleet_id = uuid.uuid4()
    sat_id = uuid.uuid4()
    alert_id = uuid.uuid4()
    db = get_session_factory()()
    try:
        from backend.app.db.models import Fleet, Satellite

        db.add(Fleet(id=fleet_id, name="Notify Fleet"))
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
        preview = AlertMitigationPreview(
            alert_id=alert_id,
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

        sent = mitigation_service.maybe_notify_mitigation_best(db, alert_id, preview)
        assert sent is True
        mock_notify.assert_called_once()
    finally:
        db.close()
    reset_engine_for_tests()


@patch("backend.app.services.mitigation_service.find_tle_by_norad_id")
def test_manual_sweep_keeps_trigger_source_manual(mock_find, ops_client):
    mock_find.return_value = parse_tle(DEMO_DEB)
    alert_id = _seed_alert(ops_client)

    response = ops_client.post(
        f"/api/v1/ops/alerts/{alert_id}/mitigation-sweep",
        json={},
    )
    assert response.status_code == 201
    assert response.json()["items"][0]["trigger_source"] == "manual"


@patch("backend.app.services.pc_refinement_service.find_tle_by_norad_id")
@patch("backend.app.services.pc_refinement_service.maybe_escalate_after_refine")
@patch("backend.app.tasks.mitigation_tasks.mitigation_sweep_task")
def test_refine_task_chains_sweep_enqueue(mock_task, mock_escalate, mock_find, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("AUTO_MITIGATION_SWEEP_ENABLED", "true")
    monkeypatch.setenv("AUTO_MITIGATION_SWEEP_ON_ESCALATION_ONLY", "true")
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)

    mock_find.return_value = parse_tle(DEMO_DEB)
    mock_escalate.return_value = True

    fleet_id = uuid.uuid4()
    sat_id = uuid.uuid4()
    alert_id = uuid.uuid4()
    db = get_session_factory()()
    try:
        from backend.app.db.models import Fleet, Satellite

        db.add(Fleet(id=fleet_id, name="Chain Fleet"))
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
        db.commit()
    finally:
        db.close()

    from backend.app.tasks.pc_refinement_tasks import refine_alert_pc_task

    result = refine_alert_pc_task(str(alert_id))

    assert result.get("mitigation_sweep_enqueued") is True
    mock_task.delay.assert_called_once_with(str(alert_id))
    reset_engine_for_tests()
