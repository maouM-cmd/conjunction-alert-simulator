"""Compare Space-Track CDM alert with CAS computation."""

from __future__ import annotations

from backend.app.services.cdm_compare import CdmCompareResult, compare_cdm_with_tles
from backend.app.services.cdm_export import cdm_public_to_kvn
from backend.app.services.spacetrack_cdm_fetcher import CdmPublicRecord, enrich_record_with_rtn
from backend.app.services.tle_fetcher import find_tle_by_norad_id
from backend.app.services.tle_parser import parse_tle


def _resolve_debris_norad(satellite_norad: int, record: CdmPublicRecord) -> int:
    if record.sat1_id == satellite_norad:
        return record.sat2_id
    if record.sat2_id == satellite_norad:
        return record.sat1_id
    raise ValueError(
        f"衛星 NORAD {satellite_norad} は CDM の SAT_1_ID/SAT_2_ID に含まれていません。"
    )


def compare_cdm_alert(
    satellite_tle: str,
    record: CdmPublicRecord,
    duration_days: float = 7.0,
    step_minutes: int = 1,
    sigma_km: float | None = None,
) -> tuple[CdmCompareResult, str]:
    satellite = parse_tle(satellite_tle)
    debris_norad = _resolve_debris_norad(satellite.norad_id, record)
    debris = find_tle_by_norad_id(debris_norad)
    if debris is None:
        raise LookupError(
            f"NORAD {debris_norad} の TLE がカタログに見つかりません。"
        )

    cdm_text = cdm_public_to_kvn(enrich_record_with_rtn(record))
    result = compare_cdm_with_tles(
        cdm_text,
        satellite_tle,
        debris.text,
        duration_days=duration_days,
        step_minutes=step_minutes,
        sigma_km=sigma_km,
    )
    return result, debris.text
