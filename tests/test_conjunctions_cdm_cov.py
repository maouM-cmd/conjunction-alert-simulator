"""Tests for CDM covariance on /conjunctions (Phase 5C)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.tle_fetcher import CatalogMeta
from backend.app.services.tle_parser import parse_tle

SAMPLES = __import__("pathlib").Path(__file__).resolve().parents[1] / "samples"

DEMO_SAT = (SAMPLES / "demo-satellite.tle").read_text(encoding="utf-8").strip()
DEMO_DEB = (SAMPLES / "demo-debris.tle").read_text(encoding="utf-8").strip()
EXAMPLE_CDM = (SAMPLES / "example.cdm").read_text(encoding="utf-8").strip()

client = TestClient(app)


def _fake_catalog():
    debris = parse_tle(DEMO_DEB)
    meta = CatalogMeta(provider="test", degraded=False, fallback=False)
    return [debris], meta


@patch("backend.app.services.analysis.fetch_debris_catalog", side_effect=_fake_catalog)
def test_conjunctions_apply_cdm_covariance(_mock_fetch):
    response = client.post(
        "/api/v1/conjunctions",
        json={
            "tle": DEMO_SAT,
            "duration_days": 7.0,
            "threshold_km": 500.0,
            "step_minutes": 5,
            "cdm_text": EXAMPLE_CDM,
            "apply_cdm_covariance": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["conjunctions"]
    matched = [
        c
        for c in data["conjunctions"]
        if c["debris_name"] and "COSMOS" in c["debris_name"].upper()
    ]
    assert matched, "expected demo debris conjunction"
    assert matched[0]["sigma_source"] == "cdm_covariance"
    assert matched[0]["pc_method_used"] == "encounter_advanced"
    assert matched[0]["covariance_source"] == "cdm_encounter"


@patch("backend.app.services.analysis.fetch_debris_catalog", side_effect=_fake_catalog)
def test_apply_cdm_covariance_requires_cdm_text(_mock_fetch):
    response = client.post(
        "/api/v1/conjunctions",
        json={
            "tle": DEMO_SAT,
            "apply_cdm_covariance": True,
        },
    )
    assert response.status_code == 400


def test_resolve_debris_norad_from_cdm():
    from backend.app.services.cdm_parser import parse_cdm
    from backend.app.services.cdm_pc_enrichment import resolve_debris_norad_from_cdm
    from backend.app.services.conjunction import ConjunctionEvent
    from datetime import datetime, timezone

    satellite = parse_tle(DEMO_SAT)
    cdm = parse_cdm(EXAMPLE_CDM)
    events = [
        ConjunctionEvent(
            debris_norad_id=35602,
            debris_name="COSMOS 2251 DEB",
            debris_tle=DEMO_DEB,
            tca=datetime.now(timezone.utc),
            miss_distance_km=1.0,
            relative_velocity_kms=7.0,
            risk_level="low",
        )
    ]
    assert resolve_debris_norad_from_cdm(satellite, cdm, events) == 35602
