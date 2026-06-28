"""Tests for altitude prefilter API (Phase 7C)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.propagator import OrbitPoint
from backend.app.services.tle_fetcher import CatalogMeta
from backend.app.services.tle_parser import parse_tle

SAMPLES = __import__("pathlib").Path(__file__).resolve().parents[1] / "samples"

DEMO_SAT = (SAMPLES / "demo-satellite.tle").read_text(encoding="utf-8").strip()
DEMO_DEB = (SAMPLES / "demo-debris.tle").read_text(encoding="utf-8").strip()

GEO_TLE = """WORLDSTAR 1
1 24732U 97002A   25179.51852101  .00000069  00000+0  00000+0 0  9994
2 24732   0.0417  91.9978 0002237  62.0810 301.0602  1.00273214 98345"""

client = TestClient(app)


def _tle_with_norad(base_text: str, norad: int, name: str | None = None) -> str:
    parsed = parse_tle(base_text)
    line1 = parsed.line1.replace(str(parsed.norad_id), str(norad), 1)
    line2 = parsed.line2.replace(f"{parsed.norad_id:5d}", f"{norad:5d}", 1)
    label = name or f"DEB {norad}"
    return f"{label}\n{line1}\n{line2}"


def _large_catalog() -> list:
    """501+ debris: few LEO + many GEO so altitude prefilter shrinks candidates."""
    leo = [parse_tle(_tle_with_norad(DEMO_DEB, 34000 + i)) for i in range(50)]
    geo = [parse_tle(GEO_TLE)] * 451
    # unique norad for geo clones
    geo_unique = []
    for i, _ in enumerate(geo):
        norad = 35000 + i
        geo_unique.append(parse_tle(_tle_with_norad(GEO_TLE, norad, f"GEO {norad}")))
    return leo + geo_unique


def _fake_large_catalog():
    debris = _large_catalog()
    meta = CatalogMeta(provider="test", degraded=False, fallback=False)
    return debris, meta


def _fake_small_catalog():
    debris = [parse_tle(DEMO_DEB)]
    meta = CatalogMeta(provider="test", degraded=False, fallback=False)
    return debris, meta


def _fast_orbit_point() -> OrbitPoint:
    t = datetime.now(timezone.utc)
    pos = (7000.0, 0.0, 0.0)
    vel = (0.0, 7.5, 0.0)
    return OrbitPoint(time=t, position_km=pos, velocity_kms=vel)


@patch("backend.app.services.analysis.propagate_orbit")
@patch("backend.app.services.analysis.fetch_debris_catalog", side_effect=_fake_large_catalog)
def test_altitude_prefilter_reduces_candidates(_mock_fetch, mock_propagate):
    mock_propagate.return_value = [_fast_orbit_point()]

    response_on = client.post(
        "/api/v1/conjunctions",
        json={
            "tle": DEMO_SAT,
            "duration_days": 1.0,
            "threshold_km": 500.0,
            "step_minutes": 5,
            "use_altitude_prefilter": True,
        },
    )
    assert response_on.status_code == 200
    data_on = response_on.json()
    assert data_on["debris_catalog_count"] >= 501
    assert data_on["altitude_prefilter_applied"] is True
    assert data_on["debris_candidates_count"] < data_on["debris_catalog_count"]

    response_off = client.post(
        "/api/v1/conjunctions",
        json={
            "tle": DEMO_SAT,
            "duration_days": 1.0,
            "threshold_km": 500.0,
            "step_minutes": 5,
            "use_altitude_prefilter": False,
        },
    )
    assert response_off.status_code == 200
    data_off = response_off.json()
    assert data_off["altitude_prefilter_applied"] is False
    assert data_off["debris_candidates_count"] == data_off["debris_catalog_count"]


@patch("backend.app.services.analysis.propagate_orbit")
@patch("backend.app.services.analysis.fetch_debris_catalog", side_effect=_fake_small_catalog)
def test_conjunctions_response_includes_prefilter_fields(_mock_fetch, mock_propagate):
    mock_propagate.return_value = [_fast_orbit_point()]

    response = client.post(
        "/api/v1/conjunctions",
        json={"tle": DEMO_SAT, "threshold_km": 500.0, "step_minutes": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert "debris_candidates_count" in data
    assert "altitude_prefilter_applied" in data
    assert data["debris_candidates_count"] == data["debris_catalog_count"]
    assert data["altitude_prefilter_applied"] is False
