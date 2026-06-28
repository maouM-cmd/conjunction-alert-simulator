"""Tests for CDM router endpoints."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.spacetrack_cdm_fetcher import CdmFetchResult, CdmPublicRecord

client = TestClient(app)


def test_cdm_fetch_without_credentials_returns_503():
    with patch(
        "backend.app.routers.cdm.spacetrack_client.has_spacetrack_credentials",
        return_value=False,
    ):
        response = client.post(
            "/api/v1/cdm/fetch",
            json={"norad_id": 25544},
        )
    assert response.status_code == 503
    assert "Space-Track" in response.json()["detail"]


@patch("backend.app.routers.cdm.spacetrack_client.has_spacetrack_credentials", return_value=True)
@patch("backend.app.routers.cdm.fetch_cdm_public")
def test_cdm_fetch_returns_records(mock_fetch, _mock_creds):
    future_tca = datetime.now(timezone.utc) + timedelta(days=1)
    mock_fetch.return_value = CdmFetchResult(
        records=[
            CdmPublicRecord(
                cdm_id="1",
                tca=future_tca,
                pc=1e-5,
                min_range_km=2.0,
                sat1_id=25544,
                sat2_id=999,
                sat1_name="ISS",
                sat2_name="DEB",
                emergency_reportable=False,
            )
        ],
        cached=False,
        degraded=False,
    )
    response = client.post(
        "/api/v1/cdm/fetch",
        json={"norad_id": 25544, "limit": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "spacetrack"
    assert len(data["records"]) == 1
    assert data["records"][0]["sat1_id"] == 25544


SAMPLES = __import__("pathlib").Path(__file__).resolve().parents[1] / "samples"
DEMO_SAT = (SAMPLES / "demo-satellite.tle").read_text(encoding="utf-8").strip()
DEMO_DEB = (SAMPLES / "demo-debris.tle").read_text(encoding="utf-8").strip()


def test_cdm_export_endpoint():
    response = client.post(
        "/api/v1/cdm/export",
        json={
            "satellite_tle": DEMO_SAT,
            "debris_tle": DEMO_DEB,
            "tca": "2026-06-30T12:00:00Z",
            "miss_distance_km": 2.5,
            "relative_velocity_kms": 7.1,
            "pc": 1.2e-05,
            "sigma_km": 0.5,
        },
    )
    assert response.status_code == 200
    assert "CCSDS_CDM_VERS" in response.json()["cdm_text"]
