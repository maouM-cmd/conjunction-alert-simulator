"""Apply CDM RTN covariance to conjunction list events (Phase 5C)."""

from __future__ import annotations

import logging

from dataclasses import replace

from backend.app.services.cdm_parser import CdmRecord, parse_cdm
from backend.app.services.cdm_tca_shift_service import encounter_states_for_cdm
from backend.app.services.conjunction import ConjunctionEvent, resolve_risk_level
from backend.app.services.encounter_plane import encounter_covariance_from_cdm
from backend.app.services.pc_advanced import pc_from_encounter
from backend.app.services.propagator import OrbitPoint
from backend.app.services.tle_parser import ParsedTle, parse_tle

logger = logging.getLogger(__name__)


def _name_matches(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    al, bl = a.lower().strip(), b.lower().strip()
    return al in bl or bl in al or al == bl


def _designator_in_tle(designator: str | None, tle_text: str) -> bool:
    if not designator:
        return False
    compact = designator.replace("-", "").upper()
    return compact in tle_text.upper().replace("-", "")


def _cdm_side_is_satellite(
    satellite: ParsedTle,
    object_name: str | None,
    designator: str | None,
) -> bool:
    return _name_matches(satellite.name, object_name) or _designator_in_tle(
        designator, satellite.text
    )


def resolve_debris_norad_from_cdm(
    satellite: ParsedTle,
    cdm: CdmRecord,
    events: list[ConjunctionEvent],
) -> int | None:
    """Identify debris NORAD id from CDM primary/secondary and conjunction events."""
    sat1_is = _cdm_side_is_satellite(satellite, cdm.sat1_object, cdm.sat1_designator)
    sat2_is = _cdm_side_is_satellite(satellite, cdm.sat2_object, cdm.sat2_designator)

    if sat1_is and not sat2_is:
        debris_name = cdm.sat2_object
    elif sat2_is and not sat1_is:
        debris_name = cdm.sat1_object
    elif sat1_is:
        debris_name = cdm.sat2_object
    else:
        debris_name = cdm.sat2_object

    for event in events:
        if debris_name and _name_matches(debris_name, event.debris_name):
            return event.debris_norad_id
    return None


def apply_cdm_covariance_to_events(
    events: list[ConjunctionEvent],
    satellite: ParsedTle,
    cdm_text: str,
    threshold_km: float,
    sat_points: list[OrbitPoint],
    debris_propagated: list[tuple[int, str, str, list[OrbitPoint]]],
) -> list[ConjunctionEvent]:
    """Recompute Pc for the CDM-matching debris event using CDM encounter covariance."""
    cdm = parse_cdm(cdm_text)
    if cdm.covariance is None:
        logger.warning("CDM に共分散がありません。TLE σ のままです。")
        return events

    debris_norad = resolve_debris_norad_from_cdm(satellite, cdm, events)
    if debris_norad is None:
        logger.warning("CDM に一致する接近イベントが見つかりません。")
        return events

    deb_pts_by_id = {norad_id: pts for norad_id, _, _, pts in debris_propagated}
    deb_pts = deb_pts_by_id.get(debris_norad)
    if deb_pts is None:
        logger.warning("CDM 一致デブリの軌道点がありません。")
        return events

    updated: list[ConjunctionEvent] = []
    for event in events:
        if event.debris_norad_id != debris_norad:
            updated.append(event)
            continue

        r1, v1, r2, v2, r_rel, v_rel, _eval_idx, shift_applied = encounter_states_for_cdm(
            cdm, sat_points, deb_pts, event.tca_index
        )

        enc_cov = encounter_covariance_from_cdm(
            cdm.covariance, r1, v1, r2, v2, r_rel, v_rel
        )
        if enc_cov is None:
            logger.warning("CDM encounter 共分散の射影に失敗しました。")
            updated.append(event)
            continue

        c_2x2, b_2d = enc_cov
        enc_pc = pc_from_encounter(b_2d, c_2x2)
        risk = resolve_risk_level(event.miss_distance_km, threshold_km, pc=enc_pc.alfriend)
        updated.append(
            replace(
                event,
                pc=enc_pc.alfriend,
                pc_foster=enc_pc.foster,
                pc_alfriend=enc_pc.alfriend,
                pc_monte_carlo=enc_pc.monte_carlo,
                pc_method_used="encounter_advanced",
                covariance_source=(
                    "cdm_encounter_tca_shift" if shift_applied else "cdm_encounter"
                ),
                sigma_source="cdm_covariance",
                risk_level=risk,
            )
        )

    updated.sort(key=lambda e: e.pc, reverse=True)
    return updated
