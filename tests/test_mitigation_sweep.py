"""Tests for mitigation sweep and plan (Phase 10C)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import AlertMitigationPreview, AuditLog, Base, ConjunctionAlert
from backend.app.db.session import get_engine, get_session_factory, reset_engine_for_tests
from backend.app.services.alert_service import ingest_screening_results, transition_alert
from backend.app.services.analysis import ConjunctionAnalysisResult
from backend.app.services.conjunction import ConjunctionEvent
from backend.app.services.mitigation_service import (
    select_best_preview,
    transition_alert_with_preview,
)
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


@pytest.fixture
def hardened_client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.delenv("CAS_API_KEY_REQUIRED", raising=False)
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    from backend.app.main import app

    with TestClient(app) as client:
        yield client
    reset_engine_for_tests()


def _seed_open_alert(ops_client: TestClient) -> tuple[str, str]:
    fleet = ops_client.post("/api/v1/fleets", json={"name": "Sweep Fleet"}).json()
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
    return fleet["id"], alert_id


def test_select_best_preview_prefers_min_improving_delta_v():
    from backend.app.db.models import AlertMitigationPreview

    p1 = AlertMitigationPreview(
        id=uuid.uuid4(),
        alert_id=uuid.uuid4(),
        direction="prograde",
        delta_v_ms=0.05,
        before_tca=datetime.now(timezone.utc),
        before_miss_distance_km=1.0,
        after_tca=datetime.now(timezone.utc),
        after_miss_distance_km=1.5,
    )
    p2 = AlertMitigationPreview(
        id=uuid.uuid4(),
        alert_id=uuid.uuid4(),
        direction="prograde",
        delta_v_ms=0.02,
        before_tca=datetime.now(timezone.utc),
        before_miss_distance_km=1.0,
        after_tca=datetime.now(timezone.utc),
        after_miss_distance_km=1.2,
    )
    best = select_best_preview([p1, p2])
    assert best is not None
    assert best.delta_v_ms == 0.02


def test_select_best_preview_falls_back_to_max_after_miss():
    from backend.app.db.models import AlertMitigationPreview

    p1 = AlertMitigationPreview(
        id=uuid.uuid4(),
        alert_id=uuid.uuid4(),
        direction="prograde",
        delta_v_ms=0.01,
        before_tca=datetime.now(timezone.utc),
        before_miss_distance_km=2.0,
        after_tca=datetime.now(timezone.utc),
        after_miss_distance_km=1.5,
    )
    p2 = AlertMitigationPreview(
        id=uuid.uuid4(),
        alert_id=uuid.uuid4(),
        direction="prograde",
        delta_v_ms=0.02,
        before_tca=datetime.now(timezone.utc),
        before_miss_distance_km=2.0,
        after_tca=datetime.now(timezone.utc),
        after_miss_distance_km=1.8,
    )
    best = select_best_preview([p1, p2])
    assert best is not None
    assert best.delta_v_ms == 0.02


@patch("backend.app.services.mitigation_service.find_tle_by_norad_id")
def test_mitigation_sweep_creates_multiple_rows(mock_find, ops_client):
    mock_find.return_value = parse_tle(DEMO_DEB)
    _fleet_id, alert_id = _seed_open_alert(ops_client)

    response = ops_client.post(
        f"/api/v1/ops/alerts/{alert_id}/mitigation-sweep",
        json={
            "direction": "prograde",
            "delta_v_min_ms": 0.01,
            "delta_v_max_ms": 0.03,
            "delta_v_step_ms": 0.01,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["total"] == 3
    assert body["best"] is not None

    db = get_session_factory()()
    try:
        assert db.query(AlertMitigationPreview).count() == 3
        sweep_audit = (
            db.query(AuditLog).filter(AuditLog.action == "alert.mitigation_sweep").one()
        )
        assert sweep_audit.resource_id == uuid.UUID(alert_id)
    finally:
        db.close()


@patch("backend.app.services.mitigation_service.find_tle_by_norad_id")
def test_mitigation_plan_transitions_with_preview(mock_find, ops_client):
    mock_find.return_value = parse_tle(DEMO_DEB)
    _fleet_id, alert_id = _seed_open_alert(ops_client)

    ops_client.patch(
        f"/api/v1/ops/alerts/{alert_id}",
        json={"status": "acknowledged"},
    )
    ops_client.post(
        f"/api/v1/ops/alerts/{alert_id}/mitigation-preview",
        json={"direction": "prograde", "delta_v_ms": 0.01},
    )

    plan = ops_client.post(
        f"/api/v1/ops/alerts/{alert_id}/mitigation-plan",
        json={"comment": "ops review"},
    )
    assert plan.status_code == 200
    assert plan.json()["status"] == "mitigation_planned"
    assert "preview" in plan.json()["comment"]
    assert "ops review" in plan.json()["comment"]

    db = get_session_factory()()
    try:
        plan_audit = (
            db.query(AuditLog).filter(AuditLog.action == "alert.mitigation_plan").one()
        )
        assert plan_audit.resource_id == uuid.UUID(alert_id)
    finally:
        db.close()


@patch("backend.app.services.mitigation_service.find_tle_by_norad_id")
def test_mitigation_plan_without_preview_returns_400(mock_find, ops_client):
    mock_find.return_value = parse_tle(DEMO_DEB)
    _fleet_id, alert_id = _seed_open_alert(ops_client)
    ops_client.patch(
        f"/api/v1/ops/alerts/{alert_id}",
        json={"status": "acknowledged"},
    )

    response = ops_client.post(
        f"/api/v1/ops/alerts/{alert_id}/mitigation-plan",
        json={},
    )
    assert response.status_code == 400


@patch("backend.app.services.mitigation_service.find_tle_by_norad_id")
def test_mitigation_plan_from_open_returns_400(mock_find, ops_client):
    mock_find.return_value = parse_tle(DEMO_DEB)
    _fleet_id, alert_id = _seed_open_alert(ops_client)
    ops_client.post(
        f"/api/v1/ops/alerts/{alert_id}/mitigation-preview",
        json={},
    )

    response = ops_client.post(
        f"/api/v1/ops/alerts/{alert_id}/mitigation-plan",
        json={},
    )
    assert response.status_code == 400


@patch("backend.app.services.mitigation_service.find_tle_by_norad_id")
def test_get_alert_shows_latest_after_sweep(mock_find, ops_client):
    mock_find.return_value = parse_tle(DEMO_DEB)
    _fleet_id, alert_id = _seed_open_alert(ops_client)
    ops_client.post(
        f"/api/v1/ops/alerts/{alert_id}/mitigation-sweep",
        json={"delta_v_min_ms": 0.01, "delta_v_max_ms": 0.02, "delta_v_step_ms": 0.01},
    )

    detail = ops_client.get(f"/api/v1/ops/alerts/{alert_id}")
    assert detail.status_code == 200
    assert detail.json()["latest_mitigation_preview"] is not None


@patch("backend.app.services.mitigation_service.find_tle_by_norad_id")
def test_wrong_fleet_api_key_sweep_returns_403(mock_find, hardened_client, monkeypatch):
    mock_find.return_value = parse_tle(DEMO_DEB)
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    monkeypatch.setenv("CAS_ADMIN_API_KEY", "admin-secret")

    fleet_a = hardened_client.post(
        "/api/v1/fleets",
        json={"name": "Fleet A"},
        headers={"X-API-Key": "admin-secret"},
    ).json()
    fleet_b = hardened_client.post(
        "/api/v1/fleets",
        json={"name": "Fleet B"},
        headers={"X-API-Key": "admin-secret"},
    ).json()
    sat = hardened_client.post(
        f"/api/v1/fleets/{fleet_a['id']}/satellites",
        json={"tle": DEMO_SAT},
        headers={"X-API-Key": "admin-secret"},
    ).json()
    db = get_session_factory()()
    try:
        ingest_screening_results(
            db,
            run_id=uuid.uuid4(),
            fleet_id=uuid.UUID(fleet_a["id"]),
            results=[_make_result(norad_id=sat["norad_id"])],
            satellite_by_norad={sat["norad_id"]: uuid.UUID(sat["id"])},
        )
    finally:
        db.close()

    alert_id = hardened_client.get(
        f"/api/v1/ops/alerts?fleet_id={fleet_a['id']}",
        headers={"X-API-Key": "admin-secret"},
    ).json()["items"][0]["id"]
    key_b = hardened_client.post(
        f"/api/v1/fleets/{fleet_b['id']}/api-keys",
        json={"name": "B key"},
        headers={"X-API-Key": "admin-secret"},
    ).json()["api_key"]

    response = hardened_client.post(
        f"/api/v1/ops/alerts/{alert_id}/mitigation-sweep",
        json={},
        headers={"X-API-Key": key_b},
    )
    assert response.status_code == 403


def test_transition_alert_with_preview_db(db_session):
    from backend.app.services import fleet_service, mitigation_service

    db = db_session
    with patch(
        "backend.app.services.mitigation_service.find_tle_by_norad_id",
        return_value=parse_tle(DEMO_DEB),
    ):
        fleet = fleet_service.create_fleet(db, name="Plan Fleet")
        sat = fleet_service.add_satellite(db, fleet.id, name=None, norad_id=None, tle=DEMO_SAT)
        opens = ingest_screening_results(
            db,
            run_id=uuid.uuid4(),
            fleet_id=fleet.id,
            results=[_make_result(norad_id=sat.norad_id)],
            satellite_by_norad={sat.norad_id: sat.id},
        )
        alert_id = opens[0].id
        transition_alert(db, alert_id, new_status="acknowledged")
        mitigation_service.run_alert_mitigation_preview(db, alert_id)
        updated = transition_alert_with_preview(db, alert_id, comment="checked")

    assert updated.status == "mitigation_planned"
    assert updated.comment is not None
    assert "preview" in updated.comment
