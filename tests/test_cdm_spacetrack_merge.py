"""Tests for Space-Track CDM auto-merge on conjunctions (Phase 8A)."""

from datetime import datetime, timezone
from unittest.mock import patch

from backend.app.services.cdm_spacetrack_merge import record_matches_event
from backend.app.services.cdm_types import RtnVariance
from backend.app.services.conjunction import ConjunctionEvent
from backend.app.services.spacetrack_cdm_fetcher import CdmFetchResult, CdmPublicRecord
from backend.app.services.tle_parser import parse_tle

SAMPLES = __import__("pathlib").Path(__file__).resolve().parents[1] / "samples"
DEMO_SAT = (SAMPLES / "demo-satellite.tle").read_text(encoding="utf-8").strip()
DEMO_DEB = (SAMPLES / "demo-debris.tle").read_text(encoding="utf-8").strip()


def _sample_event() -> ConjunctionEvent:
    return ConjunctionEvent(
        debris_norad_id=34410,
        debris_name="COSMOS 2251 DEB",
        debris_tle=DEMO_DEB,
        tca=datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc),
        miss_distance_km=0.5,
        relative_velocity_kms=7.0,
        risk_level="high",
        pc=1e-3,
        tca_index=0,
    )


def _record_with_rtn() -> CdmPublicRecord:
    return CdmPublicRecord(
        cdm_id="123456",
        tca=datetime(2026, 6, 30, 12, 0, 0, tzinfo=timezone.utc),
        pc=8.538007e-06,
        min_range_km=102.3,
        sat1_id=25544,
        sat2_id=34410,
        sat1_name="ISS (ZARYA)",
        sat2_name="COSMOS 2251 DEB",
        emergency_reportable=False,
        relative_speed_kms=12.8079,
        sat1_rtn=RtnVariance(cr_r=0.0025, ct_t=0.004, cn_n=0.0018, cr_t=0.0003, cr_n=0.0002, ct_n=0.0004),
        sat2_rtn=RtnVariance(cr_r=0.003, ct_t=0.0055, cn_n=0.0022),
    )


def _record_without_rtn() -> CdmPublicRecord:
    return CdmPublicRecord(
        cdm_id="999999",
        tca=datetime(2026, 6, 30, 12, 0, 0, tzinfo=timezone.utc),
        pc=1.2e-05,
        min_range_km=2.5,
        sat1_id=25544,
        sat2_id=34410,
        sat1_name="ISS (ZARYA)",
        sat2_name="COSMOS 2251 DEB",
        emergency_reportable=False,
    )


def test_record_matches_event_by_norad():
    satellite = parse_tle(DEMO_SAT)
    event = _sample_event()
    assert record_matches_event(satellite, event, _record_with_rtn()) is True
    assert record_matches_event(satellite, event, _record_without_rtn()) is True


def test_record_does_not_match_unrelated_debris():
    satellite = parse_tle(DEMO_SAT)
    event = _sample_event()
    other = CdmPublicRecord(
        cdm_id="1",
        tca=None,
        pc=1e-5,
        min_range_km=1.0,
        sat1_id=25544,
        sat2_id=99999,
        sat1_name="ISS",
        sat2_name="OTHER",
        emergency_reportable=False,
    )
    assert record_matches_event(satellite, event, other) is False
