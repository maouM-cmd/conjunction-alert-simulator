"""Tests for scheduled screening (Phase 9B)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import Base
from backend.app.db.session import get_engine, get_session_factory, reset_engine_for_tests
from backend.app.services.batch_analysis import BatchAnalysisResult, BatchSummary
from backend.app.services.screening_service import (
    ValidationError,
    is_schedule_due,
    validate_cron_expression,
)

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
DEMO_SAT = (SAMPLES / "demo-satellite.tle").read_text(encoding="utf-8").strip()


def _fake_batch_result(count: int = 1, total_events: int = 2) -> BatchAnalysisResult:
    from backend.app.services.analysis import ConjunctionAnalysisResult

    results = []
    for _ in range(count):
        results.append(
            ConjunctionAnalysisResult(
                satellite=__import__(
                    "backend.app.services.tle_parser", fromlist=["parse_tle"]
                ).parse_tle(DEMO_SAT),
                events=[],
                start=datetime.now(timezone.utc),
                end=datetime.now(timezone.utc),
                threshold_km=50.0,
                debris_catalog_count=1,
                debris_candidates_count=1,
                altitude_prefilter_applied=False,
                computation_time_ms=10,
                tle_cache_stale=False,
                tle_provider="test",
            )
        )
    return BatchAnalysisResult(
        results=results,
        summary=BatchSummary(
            satellite_count=count,
            total_events=total_events,
            highest_pc=0.0,
            highest_pc_satellite="ISS",
            highest_pc_debris=None,
        ),
        computation_time_ms=100,
        tle_provider="test",
        parallel=False,
        worker_count=1,
    )


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
def screening_client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")
    reset_engine_for_tests()
    from backend.app.tasks.celery_app import configure_celery_eager

    configure_celery_eager()
    engine = get_engine()
    assert engine is not None
    Base.metadata.create_all(engine)
    from backend.app.main import app

    with TestClient(app) as client:
        yield client
    reset_engine_for_tests()


def test_validate_cron_expression():
    assert validate_cron_expression("0 * * * *") == "0 * * * *"
    with pytest.raises(ValidationError, match="5フィールド"):
        validate_cron_expression("0 * *")


def test_is_schedule_due_when_never_run(db_session):
    from backend.app.services import fleet_service, screening_service

    db = db_session
    fleet = fleet_service.create_fleet(db, name="Cron Fleet")
    schedule = screening_service.create_schedule(
        db,
        fleet_id=fleet.id,
        name="Hourly",
        cron_expression="* * * * *",
    )
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    assert is_schedule_due(schedule, now) is True
    schedule.last_run_at = now
    assert is_schedule_due(schedule, now) is False


def test_screening_api_503_without_redis(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    from backend.app.main import app

    client = TestClient(app)
    response = client.get("/api/v1/screening/schedules")
    assert response.status_code == 503
    reset_engine_for_tests()


def test_create_schedule(screening_client):
    fleet = screening_client.post("/api/v1/fleets", json={"name": "Screen Fleet"}).json()
    response = screening_client.post(
        "/api/v1/screening/schedules",
        json={
            "fleet_id": fleet["id"],
            "name": "Daily",
            "cron_expression": "0 0 * * *",
            "threshold_km": 50.0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Daily"
    assert data["cron_expression"] == "0 0 * * *"


def test_list_and_delete_schedule(screening_client):
    fleet = screening_client.post("/api/v1/fleets", json={"name": "List Fleet"}).json()
    created = screening_client.post(
        "/api/v1/screening/schedules",
        json={
            "fleet_id": fleet["id"],
            "name": "To Delete",
            "cron_expression": "0 12 * * *",
        },
    ).json()
    listing = screening_client.get("/api/v1/screening/schedules")
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    delete = screening_client.delete(f"/api/v1/screening/schedules/{created['id']}")
    assert delete.status_code == 204
    assert screening_client.get(f"/api/v1/screening/schedules/{created['id']}").status_code == 404


@patch(
    "backend.app.services.screening_orchestrator.run_batch_conjunction_analysis",
    return_value=_fake_batch_result(1),
)
def test_manual_run_completes(mock_batch, screening_client):
    fleet = screening_client.post("/api/v1/fleets", json={"name": "Run Fleet"}).json()
    screening_client.post(
        f"/api/v1/fleets/{fleet['id']}/satellites",
        json={"tle": DEMO_SAT},
    )
    schedule = screening_client.post(
        "/api/v1/screening/schedules",
        json={
            "fleet_id": fleet["id"],
            "name": "Manual",
            "cron_expression": "0 0 * * *",
        },
    ).json()
    trigger = screening_client.post(f"/api/v1/screening/schedules/{schedule['id']}/run")
    assert trigger.status_code == 202
    run_id = trigger.json()["id"]
    run = screening_client.get(f"/api/v1/screening/runs/{run_id}").json()
    assert run["status"] == "completed"
    assert run["satellite_count"] == 1
    assert run["event_count"] == 2
    mock_batch.assert_called_once()



def test_mark_run_dead_letter(db_session):
    from backend.app.services import fleet_service, screening_service

    db = db_session
    fleet = fleet_service.create_fleet(db, name="DL Fleet")
    schedule = screening_service.create_schedule(
        db,
        fleet_id=fleet.id,
        name="DL",
        cron_expression="0 0 * * *",
    )
    run = screening_service.create_run(db, fleet_id=fleet.id, schedule_id=schedule.id)
    screening_service.mark_run_failed(
        db, run, error_message="failed", dead_letter=True, retry_count=3
    )
    updated = screening_service.get_run(db, run.id)
    assert updated.status == "dead_letter"
    assert updated.retry_count == 3


@patch(
    "backend.app.services.screening_orchestrator.run_batch_conjunction_analysis",
    return_value=_fake_batch_result(50, total_events=1),
)
def test_run_chunks_large_fleet(mock_batch, screening_client, monkeypatch):
    monkeypatch.setenv("SCREENING_CHUNK_SIZE", "50")
    fleet = screening_client.post("/api/v1/fleets", json={"name": "Big Fleet"}).json()
    for i in range(51):
        screening_client.post(
            f"/api/v1/fleets/{fleet['id']}/satellites",
            json={"tle": DEMO_SAT, "norad_id": 91000 + i},
        )
    schedule = screening_client.post(
        "/api/v1/screening/schedules",
        json={
            "fleet_id": fleet["id"],
            "name": "Big",
            "cron_expression": "0 0 * * *",
        },
    ).json()
    run_id = screening_client.post(
        f"/api/v1/screening/schedules/{schedule['id']}/run"
    ).json()["id"]
    run = screening_client.get(f"/api/v1/screening/runs/{run_id}").json()
    assert run["degraded"] is False
    assert run["satellite_count"] == 51
    assert run["status"] == "completed"
    assert mock_batch.call_count == 2


@patch(
    "backend.app.services.screening_orchestrator.run_batch_conjunction_analysis",
    side_effect=RuntimeError("catalog unavailable"),
)
def test_run_failed_status_on_error(mock_batch, db_session):
    from backend.app.services import fleet_service, screening_runner, screening_service

    db = db_session
    fleet = fleet_service.create_fleet(db, name="Fail Fleet")
    fleet_service.add_satellite(db, fleet.id, name=None, norad_id=None, tle=DEMO_SAT)
    schedule = screening_service.create_schedule(
        db,
        fleet_id=fleet.id,
        name="Fail",
        cron_expression="0 0 * * *",
    )
    run = screening_service.create_run(db, fleet_id=fleet.id, schedule_id=schedule.id)
    with pytest.raises(screening_runner.ScreeningRunnerError):
        screening_runner.execute_screening_run(db, run.id)
    updated = screening_service.get_run(db, run.id)
    assert updated.status == "failed"
    assert "catalog unavailable" in (updated.error_message or "")


def test_auto_spacetrack_requires_advanced_pc(screening_client):
    fleet = screening_client.post("/api/v1/fleets", json={"name": "CDM Fleet"}).json()
    response = screening_client.post(
        "/api/v1/screening/schedules",
        json={
            "fleet_id": fleet["id"],
            "name": "Bad CDM",
            "cron_expression": "0 0 * * *",
            "auto_spacetrack_cdm": True,
            "use_advanced_pc": False,
        },
    )
    assert response.status_code == 400


def test_list_runs_filter(screening_client):
    fleet = screening_client.post("/api/v1/fleets", json={"name": "Runs Fleet"}).json()
    screening_client.post(
        "/api/v1/screening/schedules",
        json={
            "fleet_id": fleet["id"],
            "name": "Runs",
            "cron_expression": "0 0 * * *",
        },
    )
    response = screening_client.get(f"/api/v1/screening/runs?fleet_id={fleet['id']}")
    assert response.status_code == 200
    assert "items" in response.json()
