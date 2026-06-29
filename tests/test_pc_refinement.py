"""Tests for alert-linked Pc refinement (Phase 10D)."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import AlertPcRefinement, AuditLog, Base
from backend.app.db.session import get_engine, get_session_factory, reset_engine_for_tests
from backend.app.services.alert_service import ingest_screening_results
from backend.app.services.analysis import ConjunctionAnalysisResult
from backend.app.services.conjunction import ConjunctionEvent
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


def _seed_alert(ops_client: TestClient) -> tuple[dict, dict, str]:
    fleet = ops_client.post("/api/v1/fleets", json={"name": "Pc Fleet"}).json()
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
    listing = ops_client.get(f"/api/v1/ops/alerts?fleet_id={fleet['id']}")
    alert_id = listing.json()["items"][0]["id"]
    return fleet, sat, alert_id


@patch("backend.app.services.pc_refinement_service.find_tle_by_norad_id")
def test_pc_refine_tle_rtn_fallback(mock_find, ops_client):
    mock_find.return_value = parse_tle(DEMO_DEB)
    fleet, _sat, alert_id = _seed_alert(ops_client)

    response = ops_client.post(f"/api/v1/ops/alerts/{alert_id}/pc-refine")
    assert response.status_code == 201
    body = response.json()
    assert body["alert_id"] == alert_id
    assert body["pc_method"] == "tle_rtn"
    assert body["covariance_source"] == "tle_age"
    assert body["pc_screening"] == pytest.approx(1e-4)
    assert body["pc_refined"] >= 0
    assert body["miss_distance_km"] >= 0

    db = get_session_factory()()
    try:
        assert db.query(AlertPcRefinement).count() == 1
        audit = db.query(AuditLog).filter(AuditLog.action == "alert.pc_refine").one()
        assert audit.resource_id == uuid.UUID(alert_id)
    finally:
        db.close()

    listing = ops_client.get(f"/api/v1/ops/alerts?fleet_id={fleet['id']}")
    assert listing.json()["items"][0]["latest_pc_refinement"] is not None


@patch("backend.app.services.pc_refinement_service.find_tle_by_norad_id")
@patch("backend.app.services.pc_refinement_service.apply_spacetrack_cdm_to_events")
def test_pc_refine_cdm_rtn_path(mock_cdm, mock_find, ops_client):
    mock_find.return_value = parse_tle(DEMO_DEB)

    def _fake_cdm(events, *_args, **_kwargs):
        event = replace(
            events[0],
            sigma_source="cdm_covariance",
            pc_foster=2.5e-5,
            pc=1e-4,
        )
        return [event], 1, 1, False

    mock_cdm.side_effect = _fake_cdm
    _fleet, _sat, alert_id = _seed_alert(ops_client)

    response = ops_client.post(f"/api/v1/ops/alerts/{alert_id}/pc-refine")
    assert response.status_code == 201
    body = response.json()
    assert body["pc_method"] == "cdm_rtn"
    assert body["covariance_source"] == "spacetrack_cdm"
    assert body["pc_refined"] == pytest.approx(2.5e-5)


@patch("backend.app.services.pc_refinement_service.find_tle_by_norad_id")
def test_list_pc_refinements(mock_find, ops_client):
    mock_find.return_value = parse_tle(DEMO_DEB)
    _fleet, _sat, alert_id = _seed_alert(ops_client)

    ops_client.post(f"/api/v1/ops/alerts/{alert_id}/pc-refine")
    ops_client.post(f"/api/v1/ops/alerts/{alert_id}/pc-refine")

    listing = ops_client.get(f"/api/v1/ops/alerts/{alert_id}/pc-refinements")
    assert listing.status_code == 200
    data = listing.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@patch("backend.app.services.pc_refinement_service.find_tle_by_norad_id")
def test_get_alert_includes_latest_pc_refinement(mock_find, ops_client):
    mock_find.return_value = parse_tle(DEMO_DEB)
    _fleet, _sat, alert_id = _seed_alert(ops_client)
    ops_client.post(f"/api/v1/ops/alerts/{alert_id}/pc-refine")

    detail = ops_client.get(f"/api/v1/ops/alerts/{alert_id}")
    assert detail.status_code == 200
    latest = detail.json()["latest_pc_refinement"]
    assert latest is not None
    assert latest["pc_method"] in ("tle_rtn", "cdm_rtn")


@patch("backend.app.services.pc_refinement_service.find_tle_by_norad_id")
def test_pc_refine_debris_not_found(mock_find, ops_client):
    mock_find.return_value = None
    _fleet, _sat, alert_id = _seed_alert(ops_client)

    response = ops_client.post(f"/api/v1/ops/alerts/{alert_id}/pc-refine")
    assert response.status_code == 404


@patch("backend.app.services.pc_refinement_service.find_tle_by_norad_id")
def test_wrong_fleet_api_key_returns_403(mock_find, hardened_client, monkeypatch):
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

    key_b = hardened_client.post(
        f"/api/v1/fleets/{fleet_b['id']}/api-keys",
        json={"name": "B key"},
        headers={"X-API-Key": "admin-secret"},
    ).json()["api_key"]

    alert_id = hardened_client.get(
        f"/api/v1/ops/alerts?fleet_id={fleet_a['id']}",
        headers={"X-API-Key": "admin-secret"},
    ).json()["items"][0]["id"]

    response = hardened_client.post(
        f"/api/v1/ops/alerts/{alert_id}/pc-refine",
        headers={"X-API-Key": key_b},
    )
    assert response.status_code == 403


def test_pc_refine_unknown_alert(ops_client):
    response = ops_client.post(f"/api/v1/ops/alerts/{uuid.uuid4()}/pc-refine")
    assert response.status_code == 404
