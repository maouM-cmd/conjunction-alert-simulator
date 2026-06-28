"""Compare CDM external values with CAS SGP4 computation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from backend.app.services.cdm_covariance import sigma_from_cdm_rtn
from backend.app.services.cdm_parser import CdmRecord, parse_cdm
from backend.app.services.conjunction import find_closest_approach
from backend.app.services.encounter_plane import encounter_covariance_from_cdm
from backend.app.services.pc_advanced import EncounterPcResult, pc_from_encounter
from backend.app.services.pc_calculator import compute_pc_for_conjunction, sigma_from_tle_age
from backend.app.services.propagator import propagate_orbit
from backend.app.services.tle_parser import parse_tle

SigmaSource = Literal["manual", "cdm_covariance", "tle_age"]
PcMethodUsed = Literal["foster_only", "encounter_advanced"]


@dataclass(frozen=True)
class PcMethods:
    foster: float | None
    alfriend: float | None
    monte_carlo: float | None


@dataclass(frozen=True)
class CdmCompareResult:
    cdm: CdmRecord
    cas_miss_distance_km: float
    cas_pc: float
    cas_relative_velocity_kms: float
    cas_tca: str
    cas_sigma_km: float
    sigma_source: SigmaSource
    delta_miss_km: float | None
    delta_pc_ratio: float | None
    pc_methods: PcMethods
    pc_method_used: PcMethodUsed
    encounter_miss_km: float | None


def _state_at_index(points, idx: int) -> tuple[np.ndarray, np.ndarray]:
    p = points[idx]
    return np.array(p.position_km, dtype=float), np.array(p.velocity_kms, dtype=float)


def _resolve_sigma_foster_only(
    cdm: CdmRecord,
    satellite,
    debris,
    analysis_time,
    sigma_km: float | None,
) -> tuple[float, SigmaSource]:
    if sigma_km is not None:
        return sigma_km, "manual"
    if cdm.covariance is not None:
        cdm_sigma = sigma_from_cdm_rtn(cdm.covariance)
        if cdm_sigma is not None:
            return cdm_sigma, "cdm_covariance"
    return sigma_from_tle_age(satellite, debris, analysis_time), "tle_age"


def compare_cdm_with_tles(
    cdm_text: str,
    satellite_tle: str,
    debris_tle: str,
    duration_days: float = 7.0,
    step_minutes: int = 1,
    sigma_km: float | None = None,
) -> CdmCompareResult:
    cdm = parse_cdm(cdm_text)
    satellite = parse_tle(satellite_tle)
    debris = parse_tle(debris_tle)

    from backend.app.services.analysis import _utc_now

    start = _utc_now()
    sat_pts = propagate_orbit(satellite, start, duration_days, step_minutes)
    deb_pts = propagate_orbit(debris, start, duration_days, step_minutes)
    ca = find_closest_approach(sat_pts, deb_pts)

    r1, v1 = _state_at_index(sat_pts, ca.index)
    r2, v2 = _state_at_index(deb_pts, ca.index)
    r_rel = r2 - r1
    v_rel = v2 - v1

    pc_methods = PcMethods(foster=None, alfriend=None, monte_carlo=None)
    pc_method_used: PcMethodUsed = "foster_only"
    encounter_miss_km: float | None = None
    cas_pc: float
    cas_sigma_km: float
    sigma_source: SigmaSource

    if sigma_km is None and cdm.covariance is not None:
        enc = encounter_covariance_from_cdm(
            cdm.covariance, r1, v1, r2, v2, r_rel, v_rel
        )
        if enc is not None:
            c_2x2, b_2d = enc
            enc_pc: EncounterPcResult = pc_from_encounter(b_2d, c_2x2)
            pc_methods = PcMethods(
                foster=enc_pc.foster,
                alfriend=enc_pc.alfriend,
                monte_carlo=enc_pc.monte_carlo,
            )
            pc_method_used = "encounter_advanced"
            encounter_miss_km = enc_pc.b_scalar_km
            cas_pc = enc_pc.alfriend
            cas_sigma_km = enc_pc.sigma_equiv_km
            sigma_source = "cdm_covariance"
        else:
            cas_sigma_km, sigma_source = _resolve_sigma_foster_only(
                cdm, satellite, debris, ca.tca, sigma_km
            )
            cas_pc = compute_pc_for_conjunction(
                ca.miss_distance_km,
                satellite,
                debris,
                ca.tca,
                sigma_km=cas_sigma_km,
            )
            pc_methods = PcMethods(foster=cas_pc, alfriend=None, monte_carlo=None)
    else:
        cas_sigma_km, sigma_source = _resolve_sigma_foster_only(
            cdm, satellite, debris, ca.tca, sigma_km
        )
        foster_pc_val = compute_pc_for_conjunction(
            ca.miss_distance_km,
            satellite,
            debris,
            ca.tca,
            sigma_km=cas_sigma_km,
        )
        cas_pc = foster_pc_val
        pc_methods = PcMethods(foster=foster_pc_val, alfriend=None, monte_carlo=None)

    delta_miss = None
    if cdm.miss_distance_km is not None:
        delta_miss = ca.miss_distance_km - cdm.miss_distance_km

    delta_pc_ratio = None
    if cdm.pc_external and cdm.pc_external > 0:
        delta_pc_ratio = cas_pc / cdm.pc_external

    return CdmCompareResult(
        cdm=cdm,
        cas_miss_distance_km=ca.miss_distance_km,
        cas_pc=cas_pc,
        cas_relative_velocity_kms=ca.relative_velocity_kms,
        cas_tca=ca.tca.isoformat().replace("+00:00", "Z"),
        cas_sigma_km=cas_sigma_km,
        sigma_source=sigma_source,
        delta_miss_km=delta_miss,
        delta_pc_ratio=delta_pc_ratio,
        pc_methods=pc_methods,
        pc_method_used=pc_method_used,
        encounter_miss_km=encounter_miss_km,
    )
