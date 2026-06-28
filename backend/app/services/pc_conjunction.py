"""Encounter-plane Pc for TLE pair conjunction events."""

from __future__ import annotations

import numpy as np

from backend.app.services.encounter_plane import encounter_frame_rotation, miss_vector_encounter
from backend.app.services.pc_advanced import (
    BULK_ALFRIEND_N_R,
    BULK_ALFRIEND_N_THETA,
    EncounterPcResult,
    pc_from_encounter,
)
from backend.app.services.pc_calculator import (
    DEFAULT_COMBINED_RADIUS_KM,
    compute_pc_for_conjunction,
    sigma_from_tle_age,
)
from backend.app.services.propagator import OrbitPoint
from backend.app.services.tle_parser import ParsedTle


def _state_at_index(points: list[OrbitPoint], index: int) -> tuple[np.ndarray, np.ndarray]:
    p = points[index]
    return np.array(p.position_km, dtype=float), np.array(p.velocity_kms, dtype=float)


def pc_for_tle_pair_at_index(
    satellite: ParsedTle,
    debris: ParsedTle,
    sat_pts: list[OrbitPoint],
    deb_pts: list[OrbitPoint],
    tca_index: int,
    sigma_km: float | None = None,
    include_monte_carlo: bool = False,
    alfriend_grid: tuple[int, int] = (BULK_ALFRIEND_N_R, BULK_ALFRIEND_N_THETA),
    hard_body_radius_km: float = DEFAULT_COMBINED_RADIUS_KM,
) -> EncounterPcResult:
    """Compute encounter-plane Pc using isotropic sigma from TLE age (no CDM)."""
    idx = min(tca_index, len(sat_pts) - 1, len(deb_pts) - 1)
    r1, v1 = _state_at_index(sat_pts, idx)
    r2, v2 = _state_at_index(deb_pts, idx)
    r_rel = r2 - r1
    v_rel = v2 - v1
    tca_time = sat_pts[idx].time

    if sigma_km is None:
        sigma_km = sigma_from_tle_age(satellite, debris, tca_time)

    r_enc = encounter_frame_rotation(r_rel, v_rel)
    b_2d = miss_vector_encounter(r_rel, r_enc)
    c_2x2 = np.eye(2) * (sigma_km * sigma_km)

    n_r, n_theta = alfriend_grid
    return pc_from_encounter(
        b_2d,
        c_2x2,
        hard_body_radius_km,
        include_monte_carlo=include_monte_carlo,
        alfriend_n_r=n_r,
        alfriend_n_theta=n_theta,
    )


def foster_pc_for_event(
    satellite: ParsedTle,
    debris: ParsedTle,
    miss_km: float,
    analysis_time,
    sigma_km: float | None = None,
) -> float:
    """Foster-only Pc for backward-compatible enrichment."""
    return compute_pc_for_conjunction(
        miss_km,
        satellite,
        debris,
        analysis_time,
        sigma_km=sigma_km,
    )
