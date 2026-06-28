"""Tests for CDM covariance on /conjunctions (Phase 5C / 8A)."""

from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.cdm_types import RtnVariance
from backend.app.services.spacetrack_cdm_fetcher import CdmFetchResult, CdmPublicRecord
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


def _record_with_rtn() -> CdmPublicRecord:
    return CdmPublicRecord(
        cdm_id="123456",
        tca=datetime(2026, 6, 30, 12, 0, 0, tzinfo=timezone.utc),
        pc=8.538007e-06,
        min_range_km=102.3,
        sat1_id=25544,
        sat2_id=34410,
        sat1_name="ISS (ZARYA)",
        sat2_name="COSMOS 2251 DEB",
        emergency_reportable=False,
        relative_speed_kms=12.8079,
        sat1_rtn=RtnVariance(cr_r=0.0025, ct_t=0.004, cn_n=0.0018, cr_t=0.0003, cr_n=0.0002, ct_n=0.0004),
        sat2_rtn=RtnVariance(cr_r=0.003, ct_t=0.0055, cn_n=0.0022),
    )


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


@patch("backend.app.services.cdm_spacetrack_merge.spacetrack_fetcher.has_spacetrack_credentials", return_value=True)
@patch("backend.app.services.cdm_spacetrack_merge.enrich_record_with_rtn")
@patch("backend.app.services.cdm_spacetrack_merge.fetch_cdm_public")
@patch("backend.app.services.analysis.fetch_debris_catalog", side_effect=_fake_catalog)
def test_auto_spacetrack_cdm_merge(_mock_fetch, mock_fetch_cdm, mock_enrich, _mock_creds):
    mock_fetch_cdm.return_value = CdmFetchResult(
        records=[_record_with_rtn()],
        cached=False,
        degraded=False,
    )
    mock_enrich.return_value = _record_with_rtn()

    response = client.post(
        "/api/v1/conjunctions",
        json={
            "tle": DEMO_SAT,
            "duration_days": 7.0,
            "threshold_km": 500.0,
            "step_minutes": 5,
            "use_advanced_pc": True,
            "auto_spacetrack_cdm": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["spacetrack_cdm_records_fetched"] == 1
    assert data["spacetrack_cdm_events_merged"] == 1
    matched = [
        c
        for c in data["conjunctions"]
        if c["debris_name"] and "COSMOS" in c["debris_name"].upper()
    ]
    assert matched
    assert matched[0]["sigma_source"] == "cdm_covariance"


@patch("backend.app.services.cdm_spacetrack_merge.spacetrack_fetcher.has_spacetrack_credentials", return_value=False)
@patch("backend.app.services.analysis.fetch_debris_catalog", side_effect=_fake_catalog)
def test_auto_spacetrack_cdm_without_credentials(_mock_fetch, _mock_creds):
    response = client.post(
        "/api/v1/conjunctions",
        json={
            "tle": DEMO_SAT,
            "duration_days": 7.0,
            "threshold_km": 500.0,
            "step_minutes": 5,
            "use_advanced_pc": True,
            "auto_spacetrack_cdm": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["spacetrack_cdm_records_fetched"] == 0
    assert data["spacetrack_cdm_events_merged"] == 0


@patch("backend.app.services.analysis.fetch_debris_catalog", side_effect=_fake_catalog)
def test_auto_spacetrack_cdm_requires_advanced_pc(_mock_fetch):
    response = client.post(
        "/api/v1/conjunctions",
        json={
            "tle": DEMO_SAT,
            "auto_spacetrack_cdm": True,
        },
    )
    assert response.status_code == 400
