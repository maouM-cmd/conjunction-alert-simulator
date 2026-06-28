"""Build CDM KVN text from CAS conjunction events or Space-Track summaries."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.services.pc_calculator import sigma_from_tle_age
from backend.app.services.spacetrack_cdm_fetcher import CdmPublicRecord
from backend.app.services.tle_parser import ParsedTle, parse_tle


def _tca_to_cdm_string(tca: datetime) -> str:
    tca = tca.astimezone(timezone.utc) if tca.tzinfo else tca.replace(tzinfo=timezone.utc)
    doy = tca.timetuple().tm_yday
    sec = tca.second + tca.microsecond / 1e6
    return f"{tca.year}/{doy:03d}/{tca.hour:02d}:{tca.minute:02d}:{sec:06.3f}"


def _isotropic_rtn_lines(prefix: str, sigma_km: float) -> list[str]:
    var = sigma_km * sigma_km
    return [
        f"{prefix}_CR_R = {var:.6f} km2",
        f"{prefix}_CT_T = {var:.6f} km2",
        f"{prefix}_CN_N = {var:.6f} km2",
    ]


def conjunction_to_cdm_kvn(
    satellite: ParsedTle,
    debris: ParsedTle,
    *,
    tca: datetime,
    miss_distance_km: float,
    relative_velocity_kms: float,
    pc: float,
    sigma_km: float | None = None,
) -> str:
    if sigma_km is None:
        sigma_km = sigma_from_tle_age(satellite, debris, tca)

    now = datetime.now(timezone.utc)
    lines = [
        "CCSDS_CDM_VERS = 1.0",
        f"CREATION_DATE = {now.strftime('%Y-%m-%dT%H:%M:%S.000')}",
        "ORIGINATOR = CAS",
        f"TCA = {_tca_to_cdm_string(tca)}",
        f"MISS_DISTANCE = {miss_distance_km:.4f} km",
        f"RELATIVE_SPEED = {relative_velocity_kms:.4f} km/s",
        f"COLLISION_PROBABILITY = {pc:.6e}",
        f"SAT1_OBJECT = {satellite.name}",
        f"SAT1_OBJECT_DESIGNATOR = {satellite.norad_id}",
        f"SAT2_OBJECT = {debris.name}",
        f"SAT2_OBJECT_DESIGNATOR = {debris.norad_id}",
    ]
    lines.extend(_isotropic_rtn_lines("SAT1", sigma_km))
    lines.extend(_isotropic_rtn_lines("SAT2", sigma_km))
    return "\n".join(lines) + "\n"


def cdm_public_to_kvn(record: CdmPublicRecord) -> str:
    now = datetime.now(timezone.utc)
    lines = [
        "CCSDS_CDM_VERS = 1.0",
        f"CREATION_DATE = {now.strftime('%Y-%m-%dT%H:%M:%S.000')}",
        "ORIGINATOR = SPACE-TRACK",
    ]
    if record.tca is not None:
        lines.append(f"TCA = {_tca_to_cdm_string(record.tca)}")
    if record.min_range_km is not None:
        lines.append(f"MISS_DISTANCE = {record.min_range_km:.4f} km")
    if record.pc is not None:
        lines.append(f"COLLISION_PROBABILITY = {record.pc:.6e}")
    if record.sat1_name:
        lines.append(f"SAT1_OBJECT = {record.sat1_name}")
    lines.append(f"SAT1_OBJECT_DESIGNATOR = {record.sat1_id}")
    if record.sat2_name:
        lines.append(f"SAT2_OBJECT = {record.sat2_name}")
    lines.append(f"SAT2_OBJECT_DESIGNATOR = {record.sat2_id}")
    if record.cdm_id:
        lines.append(f"COMMENT = CDM_ID {record.cdm_id}")
    return "\n".join(lines) + "\n"


def export_from_tle_and_conjunction(
    satellite_tle: str,
    debris_tle: str,
    *,
    tca: datetime,
    miss_distance_km: float,
    relative_velocity_kms: float,
    pc: float,
    sigma_km: float | None = None,
) -> str:
    satellite = parse_tle(satellite_tle)
    debris = parse_tle(debris_tle)
    return conjunction_to_cdm_kvn(
        satellite,
        debris,
        tca=tca,
        miss_distance_km=miss_distance_km,
        relative_velocity_kms=relative_velocity_kms,
        pc=pc,
        sigma_km=sigma_km,
    )
