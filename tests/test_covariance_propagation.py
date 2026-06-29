"""Tests for TLE RTN covariance propagation (Phase 10K)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import Base
from backend.app.db.session import get_engine, reset_engine_for_tests
from backend.app.services.covariance_propagation_service import (
    delta_days_from_epoch,
    propagate_rtn_variance,
)
from backend.app.services.pc_conjunction import pc_for_tle_pair_at_index
from backend.app.services.propagator import propagate_orbit
from backend.app.services.tle_parser import parse_tle
from backend.app.services.tle_rtn_covariance import (
    encounter_covariance_from_tle_pair,
    rtn_variance_from_tle,
)

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
DEMO_SAT = (SAMPLES / "demo-satellite.tle").read_text(encoding="utf-8").strip()
DEMO_DEB = (SAMPLES / "demo-debris.tle").read_text(encoding="utf-8").strip()


def _propagate_states(tca_index: int = 10):
    sat = parse_tle(DEMO_SAT)
    deb = parse_tle(DEMO_DEB)
    start = datetime(2026, 6, 28, 0, 0, 0, tzinfo=timezone.utc)
    sat_pts = propagate_orbit(sat, start, 1.0, 5)
    deb_pts = propagate_orbit(deb, start, 1.0, 5)
    idx = min(tca_index, len(sat_pts) - 1, len(deb_pts) - 1)
    r1 = np.array(sat_pts[idx].position_km, dtype=float)
    v1 = np.array(sat_pts[idx].velocity_kms, dtype=float)
    r2 = np.array(deb_pts[idx].position_km, dtype=float)
    v2 = np.array(deb_pts[idx].velocity_kms, dtype=float)
    r_rel = r2 - r1
    v_rel = v2 - v1
    return sat, deb, sat_pts, deb_pts, idx, r1, v1, r2, v2, r_rel, v_rel, sat_pts[idx].time


def test_propagation_off_uses_static_encounter_path(monkeypatch):
    monkeypatch.setenv("COV_PROPAGATION_ENABLED", "false")
    sat, deb, _, _, _, r1, v1, r2, v2, r_rel, v_rel, when = _propagate_states()
    c_static, _ = encounter_covariance_from_tle_pair(
        sat, deb, r1, v1, r2, v2, r_rel, v_rel, when, sigma_km=1.0, use_propagation=False
    )
    c_off, _ = encounter_covariance_from_tle_pair(
        sat, deb, r1, v1, r2, v2, r_rel, v_rel, when, sigma_km=1.0, use_propagation=False
    )
    assert np.allclose(c_static, c_off)


def test_propagation_increases_variance_with_age(monkeypatch):
    monkeypatch.setenv("COV_PROPAGATION_ENABLED", "true")
    sat = parse_tle(DEMO_SAT)
    epoch = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    near = epoch + timedelta(days=1)
    far = epoch + timedelta(days=30)
    near_var = propagate_rtn_variance(sat, near, sigma_km=1.0)
    far_var = propagate_rtn_variance(sat, far, sigma_km=1.0)
    assert far_var.cr_r > near_var.cr_r
    assert far_var.ct_t > near_var.ct_t


def test_encounter_covariance_positive_definite_with_propagation(monkeypatch):
    monkeypatch.setenv("COV_PROPAGATION_ENABLED", "true")
    sat, deb, _, _, _, r1, v1, r2, v2, r_rel, v_rel, when = _propagate_states()
    c_2x2, b_2d = encounter_covariance_from_tle_pair(
        sat,
        deb,
        r1,
        v1,
        r2,
        v2,
        r_rel,
        v_rel,
        when,
        sigma_km=1.0,
        use_propagation=True,
    )
    assert c_2x2.shape == (2, 2)
    assert b_2d.shape == (2,)
    evals = np.linalg.eigvalsh(c_2x2)
    assert np.all(evals > 0)


def test_propagated_pc_not_less_than_static_for_aged_tle(monkeypatch):
    monkeypatch.setenv("COV_PROPAGATION_ENABLED", "true")
    sat, deb, sat_pts, deb_pts, idx, _, _, _, _, _, _, _ = _propagate_states()
    aged_target = datetime(2026, 12, 28, 0, 0, 0, tzinfo=timezone.utc)
    assert delta_days_from_epoch(sat, aged_target) > 30

    static = pc_for_tle_pair_at_index(
        sat,
        deb,
        sat_pts,
        deb_pts,
        idx,
        sigma_km=1.0,
        use_anisotropic_cov=True,
    )
    monkeypatch.setenv("COV_PROPAGATION_ENABLED", "true")
    propagated = pc_for_tle_pair_at_index(
        sat,
        deb,
        sat_pts,
        deb_pts,
        idx,
        sigma_km=1.0,
        use_anisotropic_cov=True,
    )
    assert propagated.foster >= static.foster


@pytest.fixture
def ops_client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    from backend.app.main import app

    with TestClient(app) as client:
        yield client
    reset_engine_for_tests()


@patch("backend.app.services.pc_refinement_service.find_tle_by_norad_id")
@patch("backend.app.services.pc_refinement_service.apply_spacetrack_cdm_to_events")
def test_pc_refinement_stores_propagated_source(mock_cdm, mock_find, ops_client, monkeypatch):
    monkeypatch.setenv("COV_PROPAGATION_ENABLED", "true")
    mock_find.return_value = parse_tle(DEMO_DEB)
    mock_cdm.side_effect = lambda events, *args, **kwargs: (events, 0, 0, False)

    fleet = ops_client.post("/api/v1/fleets", json={"name": "Cov Fleet"}).json()
    sat = ops_client.post(
        f"/api/v1/fleets/{fleet['id']}/satellites", json={"tle": DEMO_SAT}
    ).json()

    from backend.app.db.session import get_session_factory
    from backend.app.services.alert_service import ingest_screening_results
    from backend.app.services.analysis import ConjunctionAnalysisResult
    from backend.app.services.conjunction import ConjunctionEvent

    db = get_session_factory()()
    try:
        event = ConjunctionEvent(
            debris_norad_id=parse_tle(DEMO_DEB).norad_id,
            debris_name="DEB",
            debris_tle=DEMO_DEB,
            tca=datetime.now(timezone.utc),
            miss_distance_km=1.0,
            relative_velocity_kms=7.0,
            risk_level="high",
            pc=1e-4,
        )
        result = ConjunctionAnalysisResult(
            satellite=parse_tle(DEMO_SAT),
            start=datetime.now(timezone.utc),
            end=datetime.now(timezone.utc),
            threshold_km=50.0,
            events=[event],
            debris_catalog_count=1,
            debris_candidates_count=1,
            altitude_prefilter_applied=False,
            computation_time_ms=1,
            tle_cache_stale=False,
            tle_provider="test",
        )
        ingest_screening_results(
            db,
            run_id=uuid.uuid4(),
            fleet_id=uuid.UUID(fleet["id"]),
            results=[result],
            satellite_by_norad={sat["norad_id"]: uuid.UUID(sat["id"])},
        )
    finally:
        db.close()

    listing = ops_client.get(f"/api/v1/ops/alerts?fleet_id={fleet['id']}")
    alert_id = listing.json()["items"][0]["id"]
    response = ops_client.post(f"/api/v1/ops/alerts/{alert_id}/pc-refine")
    assert response.status_code == 201
    body = response.json()
    assert body["covariance_source"] == "tle_rtn_propagated"


def test_conjunctions_advanced_propagated_covariance_source(monkeypatch):
    monkeypatch.setenv("COV_PROPAGATION_ENABLED", "true")
    from backend.app.main import app

    with TestClient(app) as client:
        with patch("backend.app.services.analysis.fetch_debris_catalog") as mock_fetch:
            from backend.app.services.tle_fetcher import CatalogMeta

            mock_fetch.return_value = ([parse_tle(DEMO_DEB)], CatalogMeta(provider="test", degraded=False, fallback=False))
            response = client.post(
                "/api/v1/conjunctions",
                json={
                    "tle": DEMO_SAT,
                    "threshold_km": 500.0,
                    "duration_days": 1.0,
                    "step_minutes": 5,
                    "use_advanced_pc": True,
                    "use_anisotropic_cov": True,
                },
            )
    assert response.status_code == 200
    body = response.json()
    assert body["conjunctions"]
    assert any(c.get("covariance_source") == "tle_rtn_propagated" for c in body["conjunctions"])


def test_anisotropic_covariance_source_helper(monkeypatch):
    monkeypatch.setenv("COV_PROPAGATION_ENABLED", "false")
    from backend.app.services.covariance_propagation_service import anisotropic_covariance_source

    assert anisotropic_covariance_source() == "tle_rtn_anisotropic"
    monkeypatch.setenv("COV_PROPAGATION_ENABLED", "true")
    assert anisotropic_covariance_source() == "tle_rtn_propagated"
