"""Tests for conjunction alert ops (Phase 9C)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import Base, ConjunctionAlert
from backend.app.db.session import get_engine, reset_engine_for_tests
from backend.app.services.alert_service import ValidationError, ingest_screening_results, transition_alert
from backend.app.services.analysis import ConjunctionAnalysisResult
from backend.app.services.conjunction import ConjunctionEvent

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
DEMO_SAT = (SAMPLES / "demo-satellite.tle").read_text(encoding="utf-8").strip()


def _make_event(
    *,
    debris_norad: int = 12345,
    tca: datetime | None = None,
    pc: float = 1e-4,
    risk: str = "high",
) -> ConjunctionEvent:
    return ConjunctionEvent(
        debris_norad_id=debris_norad,
        debris_name="TEST DEB",
        debris_tle="",
        tca=tca or datetime.now(timezone.utc),
        miss_distance_km=1.0,
        relative_velocity_kms=7.0,
        risk_level=risk,
        pc=pc,
    )


def _make_result(norad_id: int = 25544, events: list[ConjunctionEvent] | None = None):
    from dataclasses import replace

    from backend.app.services.tle_parser import parse_tle

    parsed = parse_tle(DEMO_SAT)
    if norad_id != parsed.norad_id:
        parsed = replace(parsed, norad_id=norad_id)
    return ConjunctionAnalysisResult(
        satellite=parsed,
        start=datetime.now(timezone.utc),
        end=datetime.now(timezone.utc) + timedelta(days=1),
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
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    from backend.app.main import app

    with TestClient(app) as client:
        yield client
    reset_engine_for_tests()


def test_ops_api_503_without_db(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reset_engine_for_tests()
    from backend.app.main import app

    client = TestClient(app)
    assert client.get("/api/v1/ops/alerts").status_code == 503
    reset_engine_for_tests()


def test_ingest_creates_open_alert(db_session):
    from backend.app.services import fleet_service

    db = db_session
    fleet = fleet_service.create_fleet(db, name="Alert Fleet")
    sat = fleet_service.add_satellite(db, fleet.id, name=None, norad_id=None, tle=DEMO_SAT)
    run_id = __import__("uuid").uuid4()
    new_opens = ingest_screening_results(
        db,
        run_id=run_id,
        fleet_id=fleet.id,
        results=[_make_result()],
        satellite_by_norad={sat.norad_id: sat.id},
    )
    assert len(new_opens) == 1
    assert new_opens[0].status == "open"
    assert new_opens[0].debris_norad_id == 12345


def test_ingest_dedupes_within_24h(db_session):
    from backend.app.services import fleet_service

    db = db_session
    fleet = fleet_service.create_fleet(db, name="Dedupe Fleet")
    sat = fleet_service.add_satellite(db, fleet.id, name=None, norad_id=None, tle=DEMO_SAT)
    tca = datetime.now(timezone.utc)
    run_id = __import__("uuid").uuid4()
    first = ingest_screening_results(
        db,
        run_id=run_id,
        fleet_id=fleet.id,
        results=[_make_result(events=[_make_event(tca=tca, pc=1e-4)])],
        satellite_by_norad={sat.norad_id: sat.id},
    )
    assert len(first) == 1
    second = ingest_screening_results(
        db,
        run_id=run_id,
        fleet_id=fleet.id,
        results=[_make_result(events=[_make_event(tca=tca + timedelta(hours=2), pc=2e-4)])],
        satellite_by_norad={sat.norad_id: sat.id},
    )
    assert len(second) == 0
    count = db.query(ConjunctionAlert).count()
    assert count == 1
    updated = db.get(ConjunctionAlert, first[0].id)
    assert updated.pc == 2e-4


def test_ingest_new_alert_outside_24h_window(db_session):
    from backend.app.services import fleet_service

    db = db_session
    fleet = fleet_service.create_fleet(db, name="Window Fleet")
    sat = fleet_service.add_satellite(db, fleet.id, name=None, norad_id=None, tle=DEMO_SAT)
    run_id = __import__("uuid").uuid4()
    tca1 = datetime.now(timezone.utc)
    ingest_screening_results(
        db,
        run_id=run_id,
        fleet_id=fleet.id,
        results=[_make_result(events=[_make_event(tca=tca1)])],
        satellite_by_norad={sat.norad_id: sat.id},
    )
    second = ingest_screening_results(
        db,
        run_id=run_id,
        fleet_id=fleet.id,
        results=[_make_result(events=[_make_event(tca=tca1 + timedelta(hours=30))])],
        satellite_by_norad={sat.norad_id: sat.id},
    )
    assert len(second) == 1
    assert db.query(ConjunctionAlert).count() == 2


def test_transition_valid_and_invalid(db_session):
    from backend.app.services import fleet_service

    db = db_session
    fleet = fleet_service.create_fleet(db, name="Trans Fleet")
    sat = fleet_service.add_satellite(db, fleet.id, name=None, norad_id=None, tle=DEMO_SAT)
    opens = ingest_screening_results(
        db,
        run_id=__import__("uuid").uuid4(),
        fleet_id=fleet.id,
        results=[_make_result()],
        satellite_by_norad={sat.norad_id: sat.id},
    )
    alert_id = opens[0].id
    ack = transition_alert(db, alert_id, new_status="acknowledged", comment="seen")
    assert ack.status == "acknowledged"
    assert ack.comment == "seen"
    with pytest.raises(ValidationError):
        transition_alert(db, alert_id, new_status="open")


def test_ops_api_list_and_transition(ops_client):
    fleet = ops_client.post("/api/v1/fleets", json={"name": "Ops Fleet"}).json()
    sat = ops_client.post(
        f"/api/v1/fleets/{fleet['id']}/satellites", json={"tle": DEMO_SAT}
    ).json()
    from backend.app.db.session import get_session_factory
    from backend.app.services import alert_service

    db = get_session_factory()()
    try:
        alert_service.ingest_screening_results(
            db,
            run_id=__import__("uuid").uuid4(),
            fleet_id=__import__("uuid").UUID(fleet["id"]),
            results=[_make_result(norad_id=sat["norad_id"])],
            satellite_by_norad={sat["norad_id"]: __import__("uuid").UUID(sat["id"])},
        )
    finally:
        db.close()

    summary = ops_client.get(f"/api/v1/ops/fleets/{fleet['id']}/summary")
    assert summary.status_code == 200
    assert summary.json()["open_count"] == 1

    listing = ops_client.get(f"/api/v1/ops/alerts?fleet_id={fleet['id']}&status=open")
    assert listing.status_code == 200
    alert_id = listing.json()["items"][0]["id"]

    patch = ops_client.patch(
        f"/api/v1/ops/alerts/{alert_id}",
        json={"status": "acknowledged", "comment": "ops ack"},
    )
    assert patch.status_code == 200
    assert patch.json()["status"] == "acknowledged"


@patch("backend.app.services.screening_runner.run_batch_conjunction_analysis")
@patch("backend.app.services.screening_runner.notify_new_alerts")
def test_screening_runner_notifies_new_opens_only(mock_notify, mock_batch, db_session):
    from backend.app.services import fleet_service, screening_runner, screening_service

    db = db_session
    fleet = fleet_service.create_fleet(db, name="Notify Fleet")
    sat = fleet_service.add_satellite(db, fleet.id, name=None, norad_id=None, tle=DEMO_SAT)
    schedule = screening_service.create_schedule(
        db,
        fleet_id=fleet.id,
        name="Notify",
        cron_expression="0 0 * * *",
        notify_on_complete=True,
    )
    run = screening_service.create_run(db, fleet_id=fleet.id, schedule_id=schedule.id)

    from backend.app.services.batch_analysis import BatchAnalysisResult, BatchSummary

    mock_batch.return_value = BatchAnalysisResult(
        results=[_make_result(norad_id=sat.norad_id)],
        summary=BatchSummary(1, 1, 1e-4, "ISS", "DEB"),
        computation_time_ms=100,
        tle_provider="test",
        parallel=False,
        worker_count=1,
    )
    mock_notify.return_value = __import__(
        "backend.app.services.webhook_notifier", fromlist=["WebhookResult"]
    ).WebhookResult(sent=True, alert_count=1, degraded=False, message="ok")

    screening_runner.execute_screening_run(db, run.id)
    assert mock_notify.called
    new_opens = mock_notify.call_args[0][0]
    assert len(new_opens) >= 1


def test_low_risk_events_not_ingested(db_session):
    from backend.app.services import fleet_service

    db = db_session
    fleet = fleet_service.create_fleet(db, name="Low Fleet")
    sat = fleet_service.add_satellite(db, fleet.id, name=None, norad_id=None, tle=DEMO_SAT)
    opens = ingest_screening_results(
        db,
        run_id=__import__("uuid").uuid4(),
        fleet_id=fleet.id,
        results=[_make_result(events=[_make_event(pc=1e-10, risk="low")])],
        satellite_by_norad={sat.norad_id: sat.id},
    )
    assert len(opens) == 0
