"""Orchestrate conjunction analysis with optional altitude prefilter."""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

import numpy as np
from sgp4.api import jday

from backend.app.services.conjunction import ConjunctionEvent, detect_conjunctions, resolve_risk_level
from backend.app.services.pc_calculator import compute_pc_for_conjunction
from backend.app.services.propagator import OrbitPoint, create_satrec, propagate_orbit
from backend.app.services.tle_fetcher import fetch_debris_catalog, is_cache_stale, set_last_provider_label
from backend.app.services.tle_parser import ParsedTle, parse_tle

EARTH_RADIUS_KM = 6378.137
ALTITUDE_PREFILTER_KM = 200.0


@dataclass(frozen=True)
class ConjunctionAnalysisResult:
    satellite: ParsedTle
    start: datetime
    end: datetime
    threshold_km: float
    events: list[ConjunctionEvent]
    debris_catalog_count: int
    computation_time_ms: int
    tle_cache_stale: bool
    tle_provider: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _mean_altitude_km(points: list[OrbitPoint]) -> float:
    if not points:
        return 0.0
    radii = [np.linalg.norm(p.position_km) for p in points]
    return float(np.mean(radii) - EARTH_RADIUS_KM)


def _debris_altitude_at(parsed: ParsedTle, when: datetime) -> float | None:
    sat = create_satrec(parsed)
    when = when.astimezone(timezone.utc) if when.tzinfo else when.replace(tzinfo=timezone.utc)
    jd, fr = jday(
        when.year,
        when.month,
        when.day,
        when.hour,
        when.minute,
        when.second + when.microsecond / 1e6,
    )
    err, r, _ = sat.sgp4(jd, fr)
    if err != 0:
        return None
    return float(np.linalg.norm(r) - EARTH_RADIUS_KM)


def _filter_debris_by_altitude(
    debris_list: list[ParsedTle],
    sat_mean_alt_km: float,
    start: datetime,
    band_km: float = ALTITUDE_PREFILTER_KM,
) -> list[ParsedTle]:
    filtered: list[ParsedTle] = []
    for deb in debris_list:
        alt = _debris_altitude_at(deb, start)
        if alt is None:
            continue
        if abs(alt - sat_mean_alt_km) <= band_km:
            filtered.append(deb)
    return filtered


def _enrich_with_pc(
    events: list[ConjunctionEvent],
    satellite: ParsedTle,
    threshold_km: float,
    analysis_time: datetime,
    sigma_km: float | None,
) -> list[ConjunctionEvent]:
    enriched: list[ConjunctionEvent] = []
    for event in events:
        debris = parse_tle(event.debris_tle)
        pc = compute_pc_for_conjunction(
            event.miss_distance_km,
            satellite,
            debris,
            analysis_time,
            sigma_km=sigma_km,
        )
        risk = resolve_risk_level(event.miss_distance_km, threshold_km, pc=pc)
        enriched.append(replace(event, pc=pc, risk_level=risk))
    enriched.sort(key=lambda e: e.pc, reverse=True)
    return enriched


def run_conjunction_analysis(
    tle_text: str,
    duration_days: float = 7.0,
    threshold_km: float = 5.0,
    step_minutes: int = 1,
    use_altitude_prefilter: bool = True,
    sigma_km: float | None = None,
) -> ConjunctionAnalysisResult:
    t0 = time.perf_counter()
    satellite = parse_tle(tle_text)
    start = _utc_now()
    end = start + timedelta(days=duration_days)

    debris_catalog, catalog_meta = fetch_debris_catalog()
    set_last_provider_label(catalog_meta.provider)
    catalog_count = len(debris_catalog)

    debris_catalog = [d for d in debris_catalog if d.norad_id != satellite.norad_id]

    sat_points = propagate_orbit(satellite, start, duration_days, step_minutes)
    sat_mean_alt = _mean_altitude_km(sat_points)

    candidates = debris_catalog
    if use_altitude_prefilter and len(debris_catalog) > 500:
        candidates = _filter_debris_by_altitude(debris_catalog, sat_mean_alt, start)

    debris_propagated: list[tuple[int, str, str, list[OrbitPoint]]] = []
    for deb in candidates:
        try:
            pts = propagate_orbit(deb, start, duration_days, step_minutes)
            if pts:
                debris_propagated.append((deb.norad_id, deb.name, deb.text, pts))
        except ValueError:
            continue

    events = detect_conjunctions(sat_points, debris_propagated, threshold_km)
    events = _enrich_with_pc(events, satellite, threshold_km, start, sigma_km)
    events = [e for e in events if e.risk_level != "none"]

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return ConjunctionAnalysisResult(
        satellite=satellite,
        start=start,
        end=end,
        threshold_km=threshold_km,
        events=events,
        debris_catalog_count=catalog_count,
        computation_time_ms=elapsed_ms,
        tle_cache_stale=is_cache_stale() or catalog_meta.degraded,
        tle_provider=catalog_meta.provider,
    )


def run_orbit_analysis(
    tle_text: str,
    duration_days: float = 7.0,
    step_minutes: int = 5,
) -> tuple[ParsedTle, list[OrbitPoint]]:
    parsed = parse_tle(tle_text)
    start = _utc_now()
    points = propagate_orbit(parsed, start, duration_days, step_minutes)
    return parsed, points


def run_maneuver_preview(
    satellite_tle: str,
    debris_tle: str,
    direction: str,
    delta_v_ms: float,
    duration_days: float = 7.0,
    step_minutes: int = 1,
) -> tuple:
    from backend.app.services.conjunction import find_closest_approach
    from backend.app.services.propagator import (
        compute_maneuver_offset,
        propagate_orbit,
        propagate_with_velocity_offset,
    )

    satellite = parse_tle(satellite_tle)
    debris = parse_tle(debris_tle)
    start = _utc_now()

    sat_before = propagate_orbit(satellite, start, duration_days, step_minutes)
    deb_pts = propagate_orbit(debris, start, duration_days, step_minutes)
    before = find_closest_approach(sat_before, deb_pts)

    offset = compute_maneuver_offset(satellite, direction, delta_v_ms)
    sat_after = propagate_with_velocity_offset(
        satellite, start, duration_days, step_minutes, offset
    )
    after = find_closest_approach(sat_after, deb_pts)

    return before, after
