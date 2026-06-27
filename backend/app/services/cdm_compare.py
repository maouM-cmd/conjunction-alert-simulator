"""Compare CDM external values with CAS SGP4 computation."""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.services.cdm_parser import CdmRecord, parse_cdm
from backend.app.services.conjunction import find_closest_approach
from backend.app.services.pc_calculator import compute_pc_for_conjunction
from backend.app.services.propagator import propagate_orbit
from backend.app.services.tle_parser import parse_tle


@dataclass(frozen=True)
class CdmCompareResult:
    cdm: CdmRecord
    cas_miss_distance_km: float
    cas_pc: float
    cas_relative_velocity_kms: float
    cas_tca: str
    delta_miss_km: float | None
    delta_pc_ratio: float | None


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
    cas_pc = compute_pc_for_conjunction(
        ca.miss_distance_km, satellite, debris, ca.tca, sigma_km=sigma_km
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
        delta_miss_km=delta_miss,
        delta_pc_ratio=delta_pc_ratio,
    )
