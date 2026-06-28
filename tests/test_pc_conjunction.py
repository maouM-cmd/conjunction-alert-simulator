"""Tests for encounter-plane Pc on TLE pair conjunction events."""

from datetime import datetime, timezone

import numpy as np
import pytest

from backend.app.services.pc_conjunction import pc_for_tle_pair_at_index
from backend.app.services.propagator import propagate_orbit
from backend.app.services.tle_parser import parse_tle

SAMPLES = __import__("pathlib").Path(__file__).resolve().parents[1] / "samples"

DEMO_SAT = (SAMPLES / "demo-satellite.tle").read_text(encoding="utf-8").strip()
DEMO_DEB = (SAMPLES / "demo-debris.tle").read_text(encoding="utf-8").strip()


def _propagate_pair(duration_days: float = 1.0, step_minutes: int = 5):
    sat = parse_tle(DEMO_SAT)
    deb = parse_tle(DEMO_DEB)
    start = datetime(2026, 6, 28, 0, 0, 0, tzinfo=timezone.utc)
    sat_pts = propagate_orbit(sat, start, duration_days, step_minutes)
    deb_pts = propagate_orbit(deb, start, duration_days, step_minutes)
    return sat, deb, sat_pts, deb_pts


def test_pc_for_tle_pair_returns_encounter_result():
    sat, deb, sat_pts, deb_pts = _propagate_pair()
    result = pc_for_tle_pair_at_index(
        sat, deb, sat_pts, deb_pts, tca_index=10, sigma_km=1.0
    )
    assert 0.0 <= result.foster <= 1.0
    assert 0.0 <= result.alfriend <= 1.0
    assert result.b_scalar_km >= 0.0
    assert result.sigma_equiv_km == pytest.approx(1.0)


def test_include_monte_carlo_optional():
    sat, deb, sat_pts, deb_pts = _propagate_pair()
    no_mc = pc_for_tle_pair_at_index(
        sat,
        deb,
        sat_pts,
        deb_pts,
        tca_index=10,
        sigma_km=0.5,
        include_monte_carlo=False,
    )
    with_mc = pc_for_tle_pair_at_index(
        sat,
        deb,
        sat_pts,
        deb_pts,
        tca_index=10,
        sigma_km=0.5,
        include_monte_carlo=True,
    )
    assert no_mc.monte_carlo == 0.0
    assert 0.0 <= with_mc.monte_carlo <= 1.0


def test_large_separation_pc_near_zero():
    sat, deb, sat_pts, deb_pts = _propagate_pair()
    max_idx = 0
    max_dist = 0.0
    for i in range(min(len(sat_pts), len(deb_pts))):
        r1 = np.array(sat_pts[i].position_km, dtype=float)
        r2 = np.array(deb_pts[i].position_km, dtype=float)
        dist = float(np.linalg.norm(r2 - r1))
        if dist > max_dist:
            max_dist = dist
            max_idx = i

    result = pc_for_tle_pair_at_index(
        sat, deb, sat_pts, deb_pts, tca_index=max_idx, sigma_km=0.1
    )
    assert result.foster < 1e-6
    assert result.alfriend < 1e-4
