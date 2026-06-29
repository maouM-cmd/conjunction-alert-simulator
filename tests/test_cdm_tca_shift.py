"""Tests for CDM encounter covariance at CDM TCA (Phase 10M)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from dataclasses import replace

from backend.app.services.cdm_parser import parse_cdm
from backend.app.services.cdm_pc_enrichment import apply_cdm_covariance_to_events
from backend.app.services.cdm_tca_shift_service import (
    cdm_tca_shift_enabled,
    encounter_states_for_cdm,
    index_nearest_tca,
)
from backend.app.services.conjunction import ConjunctionEvent, find_closest_approach
from backend.app.services.propagator import OrbitPoint, propagate_orbit
from backend.app.services.tle_parser import parse_tle

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
DEMO_SAT = (SAMPLES / "demo-satellite.tle").read_text(encoding="utf-8").strip()
DEMO_DEB = (SAMPLES / "demo-debris.tle").read_text(encoding="utf-8").strip()
EXAMPLE_CDM = (SAMPLES / "example.cdm").read_text(encoding="utf-8").strip()


def _cdm_with_tca(tca_line: str) -> str:
    lines = []
    for line in EXAMPLE_CDM.splitlines():
        if line.startswith("TCA ="):
            lines.append(tca_line)
        else:
            lines.append(line)
    return "\n".join(lines) + "\n"


def _propagate_pair(start: datetime | None = None):
    start = start or datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc)
    satellite = parse_tle(DEMO_SAT)
    debris = parse_tle(DEMO_DEB)
    sat_pts = propagate_orbit(satellite, start, 7.0, 5)
    deb_pts = propagate_orbit(debris, start, 7.0, 5)
    ca = find_closest_approach(sat_pts, deb_pts)
    return satellite, debris, sat_pts, deb_pts, ca


def _synthetic_cosmos_event(ca, debris) -> ConjunctionEvent:
    return ConjunctionEvent(
        debris_norad_id=debris.norad_id,
        debris_name=debris.name,
        debris_tle=debris.text,
        tca=ca.tca,
        miss_distance_km=ca.miss_distance_km,
        relative_velocity_kms=ca.relative_velocity_kms,
        risk_level="low",
        pc=1e-8,
        tca_index=ca.index,
    )


def test_cdm_tca_shift_disabled_by_default(monkeypatch):
    monkeypatch.delenv("CDM_TCA_SHIFT_ENABLED", raising=False)
    assert cdm_tca_shift_enabled() is False


def test_index_nearest_tca_picks_closest_time():
    base = datetime(2026, 6, 28, 0, 0, 0, tzinfo=timezone.utc)
    sat_pts = [
        OrbitPoint(base + timedelta(minutes=5 * i), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
        for i in range(5)
    ]
    deb_pts = [
        OrbitPoint(base + timedelta(minutes=5 * i), (2.0, 0.0, 0.0), (0.0, 1.0, 0.0))
        for i in range(5)
    ]
    target = base + timedelta(minutes=12)
    assert index_nearest_tca(sat_pts, deb_pts, target) == 2


def test_shift_off_uses_fallback_index(monkeypatch):
    monkeypatch.setenv("CDM_TCA_SHIFT_ENABLED", "false")
    satellite, debris, sat_pts, deb_pts, ca = _propagate_pair()
    shifted_tca = ca.tca + timedelta(minutes=30)
    cdm_text = _cdm_with_tca(f"TCA = {shifted_tca.strftime('%Y/%j/%H:%M:%S.000')}")
    cdm = parse_cdm(cdm_text)
    *_, eval_index, shift_applied = encounter_states_for_cdm(
        cdm, sat_pts, deb_pts, ca.index
    )
    assert shift_applied is False
    assert eval_index == ca.index


def test_shift_on_uses_cdm_tca_index(monkeypatch):
    monkeypatch.setenv("CDM_TCA_SHIFT_ENABLED", "true")
    satellite, debris, sat_pts, deb_pts, ca = _propagate_pair()
    shifted_tca = ca.tca + timedelta(minutes=30)
    cdm_text = _cdm_with_tca(f"TCA = {shifted_tca.strftime('%Y/%j/%H:%M:%S.000')}")
    cdm = parse_cdm(cdm_text)
    expected_idx = index_nearest_tca(sat_pts, deb_pts, shifted_tca)
    *_, eval_index, shift_applied = encounter_states_for_cdm(
        cdm, sat_pts, deb_pts, ca.index
    )
    assert shift_applied is True
    assert eval_index == expected_idx
    assert eval_index != ca.index or shifted_tca == ca.tca


def test_apply_cdm_covariance_tca_shift_source(monkeypatch):
    satellite, debris, sat_pts, deb_pts, ca = _propagate_pair()
    shifted_tca = ca.tca + timedelta(minutes=30)
    cdm_text = _cdm_with_tca(f"TCA = {shifted_tca.strftime('%Y/%j/%H:%M:%S.000')}")
    event = _synthetic_cosmos_event(ca, debris)
    debris_propagated = [(debris.norad_id, debris.name, debris.text, deb_pts)]

    monkeypatch.setenv("CDM_TCA_SHIFT_ENABLED", "false")
    off_events = apply_cdm_covariance_to_events(
        [event],
        satellite,
        cdm_text,
        500.0,
        sat_pts,
        debris_propagated,
    )
    assert off_events[0].covariance_source == "cdm_encounter"

    monkeypatch.setenv("CDM_TCA_SHIFT_ENABLED", "true")
    on_events = apply_cdm_covariance_to_events(
        [event],
        satellite,
        cdm_text,
        500.0,
        sat_pts,
        debris_propagated,
    )
    assert on_events[0].covariance_source == "cdm_encounter_tca_shift"


def test_apply_cdm_covariance_tca_shift_can_change_pc(monkeypatch):
    satellite, debris, sat_pts, deb_pts, ca = _propagate_pair()
    shifted_tca = ca.tca + timedelta(minutes=45)
    cdm_text = _cdm_with_tca(f"TCA = {shifted_tca.strftime('%Y/%j/%H:%M:%S.000')}")
    event = _synthetic_cosmos_event(ca, debris)
    debris_propagated = [(debris.norad_id, debris.name, debris.text, deb_pts)]

    monkeypatch.setenv("CDM_TCA_SHIFT_ENABLED", "false")
    off = apply_cdm_covariance_to_events(
        [replace(event)],
        satellite,
        cdm_text,
        500.0,
        sat_pts,
        debris_propagated,
    )
    monkeypatch.setenv("CDM_TCA_SHIFT_ENABLED", "true")
    on = apply_cdm_covariance_to_events(
        [replace(event)],
        satellite,
        cdm_text,
        500.0,
        sat_pts,
        debris_propagated,
    )
    assert off[0].covariance_source == "cdm_encounter"
    assert on[0].covariance_source == "cdm_encounter_tca_shift"
    assert index_nearest_tca(sat_pts, deb_pts, shifted_tca) != ca.index
