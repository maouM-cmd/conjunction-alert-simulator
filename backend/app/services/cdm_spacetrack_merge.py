"""Apply Space-Track cdm_public records to conjunction events (Phase 8A)."""

from __future__ import annotations

import logging

from backend.app.services import spacetrack_fetcher
from backend.app.services.cdm_export import cdm_public_to_kvn
from backend.app.services.cdm_pc_enrichment import apply_cdm_covariance_to_events
from backend.app.services.conjunction import ConjunctionEvent
from backend.app.services.propagator import OrbitPoint
from backend.app.services.spacetrack_cdm_fetcher import (
    CdmPublicRecord,
    enrich_record_with_rtn,
    fetch_cdm_public,
)
from backend.app.services.tle_parser import ParsedTle

logger = logging.getLogger(__name__)

DEFAULT_CDM_FETCH_LIMIT = 25


def record_matches_event(
    satellite: ParsedTle,
    event: ConjunctionEvent,
    record: CdmPublicRecord,
) -> bool:
    ids = {record.sat1_id, record.sat2_id}
    return satellite.norad_id in ids and event.debris_norad_id in ids


def _cdm_merged_event_count(events: list[ConjunctionEvent]) -> int:
    return sum(1 for event in events if event.sigma_source == "cdm_covariance")


def apply_spacetrack_cdm_to_events(
    events: list[ConjunctionEvent],
    satellite: ParsedTle,
    threshold_km: float,
    sat_points: list[OrbitPoint],
    debris_propagated: list[tuple[int, str, str, list[OrbitPoint]]],
    *,
    pc_min: float | None = None,
    limit: int = DEFAULT_CDM_FETCH_LIMIT,
) -> tuple[list[ConjunctionEvent], int, int, bool]:
    """Fetch cdm_public for the satellite and apply RTN covariance to matching events."""
    if not spacetrack_fetcher.has_spacetrack_credentials():
        return events, 0, 0, False

    try:
        fetch_result = fetch_cdm_public(
            norad_id=satellite.norad_id,
            pc_min=pc_min,
            limit=limit,
        )
    except RuntimeError as exc:
        logger.warning("Space-Track CDM 自動マージ取得失敗: %s", exc)
        return events, 0, 0, True

    records_fetched = len(fetch_result.records)
    degraded = fetch_result.degraded
    merged_before = _cdm_merged_event_count(events)

    for record in fetch_result.records:
        if not any(record_matches_event(satellite, event, record) for event in events):
            continue

        enriched = enrich_record_with_rtn(record)
        if not enriched.has_rtn_covariance():
            logger.debug("CDM %s に RTN 共分散がありません。スキップ。", record.cdm_id)
            continue

        kvn = cdm_public_to_kvn(enriched)
        events = apply_cdm_covariance_to_events(
            events,
            satellite,
            kvn,
            threshold_km,
            sat_points,
            debris_propagated,
        )

    merged_count = _cdm_merged_event_count(events) - merged_before
    return events, records_fetched, merged_count, degraded
