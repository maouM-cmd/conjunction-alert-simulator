"""Tests for Phase 9D scale-out."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import Base
from backend.app.db.session import get_engine, get_session_factory, reset_engine_for_tests
from backend.app.services.batch_analysis import MAX_SATELLITES, BatchAnalysisResult, BatchSummary
from backend.app.services.scale_config import screening_chunk_size

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
DEMO_SAT = (SAMPLES / "demo-satellite.tle").read_text(encoding="utf-8").strip()


def _fake_batch_result(count: int = 1, total_events: int = 2) -> BatchAnalysisResult:
    from backend.app.services.analysis import ConjunctionAnalysisResult
    from backend.app.services.tle_parser import parse_tle

    parsed = parse_tle(DEMO_SAT)
    results = [
        ConjunctionAnalysisResult(
            satellite=parsed,
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
        for _ in range(count)
    ]
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
def scale_client(monkeypatch):
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


def _make_fake_sat(norad_id: int):
    from backend.app.services.tle_parser import parse_tle

    parsed = parse_tle(DEMO_SAT)

    class FakeSat:
        tle = DEMO_SAT
        norad_id = norad_id
        id = uuid.uuid4()
        name = parsed.name

    return FakeSat()


def _add_many_satellites(db, fleet_id, count: int):
    from backend.app.services import fleet_service

    for i in range(count):
        fleet_service.add_satellite(
            db,
            fleet_id,
            name=f"Sat-{i}",
            norad_id=90000 + i,
            tle=DEMO_SAT,
        )


@pytest.fixture
def db_session_eager(db_session, monkeypatch):
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from backend.app.tasks.celery_app import configure_celery_eager

    configure_celery_eager()
    yield db_session


@patch("backend.app.services.screening_orchestrator.run_batch_conjunction_analysis")
def test_fleet_51_satellites_creates_two_chunk_runs(mock_batch, db_session_eager, monkeypatch):
    monkeypatch.setenv("SCREENING_CHUNK_SIZE", "50")
    from backend.app.services import fleet_service, screening_orchestrator, screening_service

    mock_batch.side_effect = lambda tles, **kwargs: _fake_batch_result(len(tles), total_events=3)

    db = db_session_eager
    fleet = fleet_service.create_fleet(db, name="Chunk Fleet")
    _add_many_satellites(db, fleet.id, 51)

    schedule = screening_service.create_schedule(
        db,
        fleet_id=fleet.id,
        name="Chunked",
        cron_expression="0 0 * * *",
    )
    parent = screening_service.create_run(db, fleet_id=fleet.id, schedule_id=schedule.id)
    screening_orchestrator.execute_screening_run(db, parent.id)

    parent = screening_service.get_run(db, parent.id)
    assert parent.chunk_total == 2
    assert parent.status == "completed"
    assert parent.satellite_count == 51
    assert parent.event_count == 6
    assert parent.degraded is False

    children = screening_service.list_child_runs(db, parent.id)
    assert len(children) == 2
    assert children[0].chunk_index == 0
    assert children[1].chunk_index == 1
    assert all(c.status == "completed" for c in children)
    assert mock_batch.call_count == 2


@patch("backend.app.services.screening_orchestrator.run_batch_conjunction_analysis")
def test_chunk_completion_aggregates_event_count(mock_batch, db_session_eager, monkeypatch):
    monkeypatch.setenv("SCREENING_CHUNK_SIZE", "50")
    from backend.app.services import fleet_service, screening_orchestrator, screening_service

    def batch_side_effect(tles, **kwargs):
        return _fake_batch_result(len(tles), total_events=5)

    mock_batch.side_effect = batch_side_effect

    db = db_session_eager
    fleet = fleet_service.create_fleet(db, name="Agg Fleet")
    _add_many_satellites(db, fleet.id, 51)
    schedule = screening_service.create_schedule(
        db,
        fleet_id=fleet.id,
        name="Agg",
        cron_expression="0 0 * * *",
    )
    parent = screening_service.create_run(db, fleet_id=fleet.id, schedule_id=schedule.id)
    screening_orchestrator.execute_screening_run(db, parent.id)

    parent = screening_service.get_run(db, parent.id)
    assert parent.event_count == 10
    assert parent.completed_chunks == 2


def test_fleet_max_satellites_returns_409(scale_client, monkeypatch):
    monkeypatch.setenv("FLEET_MAX_SATELLITES", "2")
    fleet = scale_client.post("/api/v1/fleets", json={"name": "Cap Fleet"}).json()
    assert scale_client.post(
        f"/api/v1/fleets/{fleet['id']}/satellites",
        json={"tle": DEMO_SAT, "norad_id": 90001},
    ).status_code == 201
    assert scale_client.post(
        f"/api/v1/fleets/{fleet['id']}/satellites",
        json={"tle": DEMO_SAT, "norad_id": 90002},
    ).status_code == 201
    response = scale_client.post(
        f"/api/v1/fleets/{fleet['id']}/satellites",
        json={"tle": DEMO_SAT, "norad_id": 90003},
    )
    assert response.status_code == 409


def test_batch_api_still_limits_25_satellites(scale_client, monkeypatch):
    monkeypatch.setenv("TLE_PROVIDER", "celestrak")
    satellites = [{"tle": DEMO_SAT}] * (MAX_SATELLITES + 1)
    response = scale_client.post(
        "/api/v1/conjunctions/batch",
        json={"satellites": satellites, "duration_days": 1, "threshold_km": 50},
    )
    assert response.status_code == 422


@patch("backend.app.services.batch_analysis.fetch_debris_catalog")
def test_screening_batch_allows_50_satellites(mock_catalog, db_session, monkeypatch):
    monkeypatch.setenv("SCREENING_CHUNK_SIZE", "50")
    from backend.app.services.batch_analysis import run_batch_conjunction_analysis
    from backend.app.services.tle_fetcher import CatalogMeta

    mock_catalog.return_value = ([], CatalogMeta(provider="test", degraded=False, fallback=False))

    tles = [DEMO_SAT] * 50
    result = run_batch_conjunction_analysis(
        tles,
        duration_days=1,
        threshold_km=50,
        max_satellites=screening_chunk_size(),
    )
    assert result.summary.satellite_count == 50


def test_metrics_endpoint_returns_prometheus(scale_client):
    response = scale_client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "cas_open_alerts_total" in body
    assert "cas_info" in body
    assert "1.11.0" in body


def test_local_spacetrack_rate_limiter_enforces_interval(monkeypatch):
    from backend.app.services import spacetrack_rate_limiter

    monkeypatch.delenv("REDIS_URL", raising=False)
    spacetrack_rate_limiter.reset_redis_client_for_tests()
    spacetrack_rate_limiter._last_request_at = 0.0

    with patch("backend.app.services.spacetrack_rate_limiter.time.monotonic", return_value=0.5):
        with patch("backend.app.services.spacetrack_rate_limiter.time.sleep") as mock_sleep:
            spacetrack_rate_limiter.acquire_spacetrack_slot()
            mock_sleep.assert_called_once()
            assert mock_sleep.call_args[0][0] == pytest.approx(0.5, abs=0.01)


def test_redis_spacetrack_rate_limiter_uses_set(monkeypatch):
    from backend.app.services import spacetrack_rate_limiter

    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    spacetrack_rate_limiter.reset_redis_client_for_tests()

    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True

    with patch("redis.from_url", return_value=mock_redis):
        spacetrack_rate_limiter.reset_redis_client_for_tests()
        spacetrack_rate_limiter.acquire_spacetrack_slot()

    mock_redis.set.assert_called()


@patch(
    "backend.app.services.screening_orchestrator.run_batch_conjunction_analysis",
    return_value=_fake_batch_result(1),
)
def test_single_chunk_run_no_children(mock_batch, scale_client):
    fleet = scale_client.post("/api/v1/fleets", json={"name": "Small Fleet"}).json()
    scale_client.post(
        f"/api/v1/fleets/{fleet['id']}/satellites",
        json={"tle": DEMO_SAT},
    )
    schedule = scale_client.post(
        "/api/v1/screening/schedules",
        json={
            "fleet_id": fleet["id"],
            "name": "Small",
            "cron_expression": "0 0 * * *",
        },
    ).json()
    run_id = scale_client.post(f"/api/v1/screening/schedules/{schedule['id']}/run").json()["id"]
    run = scale_client.get(f"/api/v1/screening/runs/{run_id}").json()
    assert run["status"] == "completed"
    assert run["degraded"] is False
    listing = scale_client.get(f"/api/v1/screening/runs?fleet_id={fleet['id']}").json()
    assert listing["total"] == 1
