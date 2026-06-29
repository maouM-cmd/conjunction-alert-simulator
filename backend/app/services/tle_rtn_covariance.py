"""TLE-based RTN anisotropic covariance for encounter-plane Pc."""

from __future__ import annotations

from datetime import datetime

import numpy as np

from backend.app.services.cdm_types import RtnVariance
from backend.app.services.encounter_plane import (
    ensure_positive_definite,
    encounter_frame_rotation,
    miss_vector_encounter,
    project_covariance_to_encounter,
    rtn_variance_to_matrix,
    teme_covariance_from_rtn,
)
from backend.app.services.pc_calculator import sigma_from_tle_age
from backend.app.services.tle_parser import ParsedTle

RTN_R_SCALE = 2.0
RTN_T_SCALE = 0.5
RTN_N_SCALE = 0.5


def _base_sigma_km(
    parsed: ParsedTle,
    analysis_time: datetime,
    sigma_km: float | None,
) -> float:
    if sigma_km is not None:
        return sigma_km
    return sigma_from_tle_age(parsed, parsed, analysis_time)


def rtn_variance_from_tle(
    parsed: ParsedTle,
    analysis_time: datetime,
    sigma_km: float | None = None,
) -> RtnVariance:
    """Build diagonal RTN variance (km^2) from TLE age and anisotropic scales."""
    base = _base_sigma_km(parsed, analysis_time, sigma_km)
    return RtnVariance(
        cr_r=(base * RTN_R_SCALE) ** 2,
        ct_t=(base * RTN_T_SCALE) ** 2,
        cn_n=(base * RTN_N_SCALE) ** 2,
    )


def encounter_covariance_from_tle_pair(
    satellite: ParsedTle,
    debris: ParsedTle,
    r1: np.ndarray,
    v1: np.ndarray,
    r2: np.ndarray,
    v2: np.ndarray,
    r_rel: np.ndarray,
    v_rel: np.ndarray,
    analysis_time: datetime,
    sigma_km: float | None = None,
    *,
    use_propagation: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Build encounter-plane 2x2 covariance and miss vector from TLE RTN estimates.

    Returns (C_2x2, b_2d).
    """
    if use_propagation:
        from backend.app.services.covariance_propagation_service import propagate_rtn_variance

        rtn1 = propagate_rtn_variance(satellite, analysis_time, sigma_km)
        rtn2 = propagate_rtn_variance(debris, analysis_time, sigma_km)
    else:
        rtn1 = rtn_variance_from_tle(satellite, analysis_time, sigma_km)
        rtn2 = rtn_variance_from_tle(debris, analysis_time, sigma_km)
    c1 = rtn_variance_to_matrix(rtn1)
    c2 = rtn_variance_to_matrix(rtn2)

    cov1_teme = teme_covariance_from_rtn(c1, r1, v1)
    cov2_teme = teme_covariance_from_rtn(c2, r2, v2)
    r_enc = encounter_frame_rotation(r_rel, v_rel)
    c_2x2 = project_covariance_to_encounter(cov1_teme, cov2_teme, r_enc)
    c_2x2 = ensure_positive_definite(c_2x2)
    b_2d = miss_vector_encounter(r_rel, r_enc)
    return c_2x2, b_2d
