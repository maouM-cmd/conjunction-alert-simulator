"""Tests for screening auto Pc refinement and escalation (Phase 10E)."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import AlertPcRefinement, AuditLog, Base, ConjunctionAlert
from backend.app.db.session import get_engine, get_session_factory, reset_engine_for_tests
from backend.app.services.alert_service import ingest_screening_results
from backend.app.services.analysis import ConjunctionAnalysisResult
from backend.app.services.conjunction import ConjunctionEvent
from backend.app.services import pc_refinement_service
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


def _seed_alert(ops_client: TestClient, *, pc: float = 1e-4) -> tuple[dict, dict, str]:
    fleet = ops_client.post("/api/v1/fleets", json={"name": "Auto Pc Fleet"}).json()
    sat = ops_client.post(
        f"/api/v1/fleets/{fleet['id']}/satellites", json={"tle": DEMO_SAT}
    ).json()
    db = get_session_factory()()
    try:
        ingest_screening_results(
            db,
            run_id=uuid.uuid4(),
            fleet_id=uuid.UUID(fleet["id"]),
            results=[_make_result(norad_id=sat["norad_id"], events=[_make_event(pc=pc)])],
            satellite_by_norad={sat["norad_id"]: uuid.UUID(sat["id"])},
        )
    finally:
        db.close()
    listing = ops_client.get(f"/api/v1/ops/alerts?fleet_id={fleet['id']}")
    alert_id = listing.json()["items"][0]["id"]
    return fleet, sat, alert_id


def test_should_auto_refine_respects_env(monkeypatch):
    alert = MagicMock(spec=ConjunctionAlert)
    alert.pc = 1e-4

    monkeypatch.setenv("AUTO_PC_REFINE_ENABLED", "false")
    assert pc_refinement_service.should_auto_refine(alert) is False

    monkeypatch.setenv("AUTO_PC_REFINE_ENABLED", "true")
    monkeypatch.setenv("AUTO_PC_REFINE_PC_MIN", "1e-5")
    assert pc_refinement_service.should_auto_refine(alert) is True

    alert.pc = 1e-6
    assert pc_refinement_service.should_auto_refine(alert) is False


@patch("backend.app.tasks.pc_refinement_tasks.refine_alert_pc_task")
def test_enqueue_auto_refine_for_alerts(mock_task, monkeypatch):
    monkeypatch.setenv("AUTO_PC_REFINE_ENABLED", "true")
    monkeypatch.setenv("AUTO_PC_REFINE_PC_MIN", "1e-5")

    high = MagicMock(spec=ConjunctionAlert)
    high.id = uuid.uuid4()
    high.pc = 1e-4
    low = MagicMock(spec=ConjunctionAlert)
    low.id = uuid.uuid4()
    low.pc = 1e-8

    count = pc_refinement_service.enqueue_auto_refine_for_alerts([high, low])
    assert count == 1
    mock_task.delay.assert_called_once_with(str(high.id))


@patch("backend.app.tasks.pc_refinement_tasks.refine_alert_pc_task")
def test_enqueue_disabled(mock_task, monkeypatch):
    monkeypatch.setenv("AUTO_PC_REFINE_ENABLED", "false")
    alert = MagicMock(spec=ConjunctionAlert)
    alert.id = uuid.uuid4()
    alert.pc = 1e-3
    assert pc_refinement_service.enqueue_auto_refine_for_alerts([alert]) == 0
    mock_task.delay.assert_not_called()


@patch("backend.app.services.pc_refinement_service.find_tle_by_norad_id")
@patch("backend.app.services.pc_refinement_service.maybe_escalate_after_refine")
def test_refine_alert_pc_task_screening_auto(mock_escalate, mock_find, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)

    mock_find.return_value = parse_tle(DEMO_DEB)
    mock_escalate.return_value = False

    fleet_id = uuid.uuid4()
    sat_id = uuid.uuid4()
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
        alert = ConjunctionAlert(
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
        db.add(alert)
        db.commit()
        alert_id = alert.id
    finally:
        db.close()

    from backend.app.tasks.pc_refinement_tasks import refine_alert_pc_task

    result = refine_alert_pc_task(str(alert_id))
    assert result["trigger_source"] == "screening_auto"
    assert "refinement_id" in result

    db = get_session_factory()()
    try:
        row = db.query(AlertPcRefinement).one()
        assert row.trigger_source == "screening_auto"
        audit = db.query(AuditLog).filter(AuditLog.action == "alert.pc_refine_auto").one()
        assert audit.resource_id == alert_id
    finally:
        db.close()
    reset_engine_for_tests()


@patch("backend.app.services.webhook_notifier.notify_pc_escalation")
def test_maybe_escalate_after_refine(mock_notify, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("PC_ESCALATION_PC_MIN", "1e-5")
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

        db.add(Fleet(id=fleet_id, name="Esc Fleet"))
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
            pc_refined=2e-5,
            pc_method="tle_rtn",
            covariance_source="tle_age",
            miss_distance_km=1.0,
            trigger_source="screening_auto",
        )
        db.add(refinement)
        db.commit()
        db.refresh(refinement)

        sent = pc_refinement_service.maybe_escalate_after_refine(db, refinement)
        assert sent is True
        mock_notify.assert_called_once()
        audit = db.query(AuditLog).filter(AuditLog.action == "alert.pc_escalate").one()
        assert audit.resource_id == alert_id
    finally:
        db.close()
    reset_engine_for_tests()


@patch("backend.app.services.pc_refinement_service.find_tle_by_norad_id")
def test_manual_pc_refine_keeps_trigger_source_manual(mock_find, ops_client):
    mock_find.return_value = parse_tle(DEMO_DEB)
    _fleet, _sat, alert_id = _seed_alert(ops_client)

    response = ops_client.post(f"/api/v1/ops/alerts/{alert_id}/pc-refine")
    assert response.status_code == 201
    assert response.json()["trigger_source"] == "manual"

    detail = ops_client.get(f"/api/v1/ops/alerts/{alert_id}")
    assert detail.json()["latest_pc_refinement"]["trigger_source"] == "manual"


@patch("backend.app.services.screening_orchestrator.pc_refinement_service.enqueue_auto_refine_for_alerts")
def test_screening_orchestrator_enqueues_auto_refine(mock_enqueue, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)

    mock_enqueue.return_value = 1
    db = get_session_factory()()
    try:
        from backend.app.db.models import Fleet, ScreeningRun, ScreeningSchedule, Satellite
        from backend.app.services import screening_orchestrator

        fleet_id = uuid.uuid4()
        db.add(Fleet(id=fleet_id, name="Orch Fleet"))
        sat = Satellite(
            id=uuid.uuid4(),
            fleet_id=fleet_id,
            name="ISS",
            norad_id=25544,
            tle=DEMO_SAT,
        )
        db.add(sat)
        schedule = ScreeningSchedule(
            fleet_id=fleet_id,
            name="Daily",
            cron_expression="0 * * * *",
            threshold_km=50.0,
            notify_on_complete=False,
        )
        db.add(schedule)
        run = ScreeningRun(
            fleet_id=fleet_id,
            schedule_id=schedule.id,
            status="pending",
        )
        db.add(run)
        db.commit()

        with patch(
            "backend.app.services.screening_orchestrator._run_batch_for_satellites"
        ) as mock_batch:
            mock_batch.return_value = MagicMock(
                results=[_make_result(norad_id=25544)],
                summary=MagicMock(total_events=1),
                computation_time_ms=5,
            )
            screening_orchestrator._execute_single_chunk_on_run(
                db, run, [sat], screening_orchestrator._schedule_params(schedule), schedule
            )
        mock_enqueue.assert_called_once()
        new_opens = mock_enqueue.call_args[0][0]
        assert len(new_opens) == 1
    finally:
        db.close()
    reset_engine_for_tests()


@patch("backend.app.services.pc_refinement_service.find_tle_by_norad_id")
@patch("backend.app.services.pc_refinement_service.apply_spacetrack_cdm_to_events")
def test_alert_escalated_flag_on_listing(mock_cdm, mock_find, ops_client, monkeypatch):
    mock_find.return_value = parse_tle(DEMO_DEB)
    monkeypatch.setenv("PC_ESCALATION_PC_MIN", "1e-6")

    def _fake_cdm(events, *_args, **_kwargs):
        event = replace(
            events[0],
            sigma_source="cdm_covariance",
            pc_foster=2.5e-5,
            pc=1e-4,
        )
        return [event], 1, 1, False

    mock_cdm.side_effect = _fake_cdm
    fleet, _sat, alert_id = _seed_alert(ops_client)
    ops_client.post(f"/api/v1/ops/alerts/{alert_id}/pc-refine")

    listing = ops_client.get(f"/api/v1/ops/alerts?fleet_id={fleet['id']}")
    item = listing.json()["items"][0]
    assert item["escalated"] is True
    assert item["latest_pc_refinement"]["pc_refined"] == pytest.approx(2.5e-5)
