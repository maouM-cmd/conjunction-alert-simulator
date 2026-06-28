"""Tests for TLE RTN anisotropic encounter covariance."""

from datetime import datetime, timezone

import numpy as np
import pytest

from backend.app.services.propagator import propagate_orbit
from backend.app.services.tle_parser import parse_tle
from backend.app.services.tle_rtn_covariance import (
    RTN_N_SCALE,
    RTN_R_SCALE,
    RTN_T_SCALE,
    encounter_covariance_from_tle_pair,
    rtn_variance_from_tle,
)

SAMPLES = __import__("pathlib").Path(__file__).resolve().parents[1] / "samples"

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


def test_rtn_variance_scales():
    sat = parse_tle(DEMO_SAT)
    when = datetime(2026, 6, 28, 0, 0, 0, tzinfo=timezone.utc)
    rtn = rtn_variance_from_tle(sat, when, sigma_km=1.0)
    assert rtn.cr_r == pytest.approx((RTN_R_SCALE) ** 2)
    assert rtn.ct_t == pytest.approx((RTN_T_SCALE) ** 2)
    assert rtn.cn_n == pytest.approx((RTN_N_SCALE) ** 2)


def test_encounter_covariance_positive_definite():
    sat, deb, _, _, _, r1, v1, r2, v2, r_rel, v_rel, when = _propagate_states()
    c_2x2, b_2d = encounter_covariance_from_tle_pair(
        sat, deb, r1, v1, r2, v2, r_rel, v_rel, when, sigma_km=1.0
    )
    assert c_2x2.shape == (2, 2)
    assert b_2d.shape == (2,)
    evals = np.linalg.eigvalsh(c_2x2)
    assert np.all(evals > 0)


def test_anisotropic_pc_differs_from_isotropic():
    """Synthetic close approach: anisotropic encounter C yields different Alfriend Pc."""
    from backend.app.services.pc_advanced import pc_from_encounter

    sat = parse_tle(DEMO_SAT)
    deb = parse_tle(DEMO_DEB)
    when = datetime(2026, 6, 28, 0, 0, 0, tzinfo=timezone.utc)
    r1 = np.array([7000.0, 0.0, 0.0])
    v1 = np.array([0.0, 7.5, 0.0])
    r2 = np.array([7000.5, 0.2, 0.1])
    v2 = np.array([0.0, 7.4, 0.1])
    r_rel = r2 - r1
    v_rel = v2 - v1
    c_aniso, b_2d = encounter_covariance_from_tle_pair(
        sat, deb, r1, v1, r2, v2, r_rel, v_rel, when, sigma_km=1.0
    )
    c_iso = np.eye(2) * 1.0
    iso = pc_from_encounter(b_2d, c_iso, 0.015)
    aniso = pc_from_encounter(b_2d, c_aniso, 0.015)
    assert iso.alfriend != aniso.alfriend
    assert iso.alfriend > 0.0
    assert aniso.alfriend > 0.0
