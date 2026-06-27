"""Compare CDM external values with CAS SGP4 computation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from backend.app.services.cdm_covariance import sigma_from_cdm_rtn
from backend.app.services.cdm_parser import CdmRecord, parse_cdm
from backend.app.services.conjunction import find_closest_approach
from backend.app.services.pc_calculator import compute_pc_for_conjunction, sigma_from_tle_age
from backend.app.services.propagator import propagate_orbit
from backend.app.services.tle_parser import parse_tle

SigmaSource = Literal["manual", "cdm_covariance", "tle_age"]


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


def _resolve_sigma(
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

    resolved_sigma, sigma_source = _resolve_sigma(
        cdm, satellite, debris, ca.tca, sigma_km
    )
    cas_pc = compute_pc_for_conjunction(
        ca.miss_distance_km,
        satellite,
        debris,
        ca.tca,
        sigma_km=resolved_sigma,
    )

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
        cas_sigma_km=resolved_sigma,
        sigma_source=sigma_source,
        delta_miss_km=delta_miss,
        delta_pc_ratio=delta_pc_ratio,
    )
