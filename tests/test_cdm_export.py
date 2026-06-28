"""Tests for CDM KVN export."""

from datetime import datetime, timezone

from backend.app.services.cdm_export import (
    cdm_public_to_kvn,
    export_from_tle_and_conjunction,
)
from backend.app.services.spacetrack_cdm_fetcher import CdmPublicRecord

SAMPLES = __import__("pathlib").Path(__file__).resolve().parents[1] / "samples"
DEMO_SAT = (SAMPLES / "demo-satellite.tle").read_text(encoding="utf-8").strip()
DEMO_DEB = (SAMPLES / "demo-debris.tle").read_text(encoding="utf-8").strip()


def test_export_from_conjunction_has_required_keys():
    text = export_from_tle_and_conjunction(
        DEMO_SAT,
        DEMO_DEB,
        tca=datetime(2026, 6, 30, 12, 0, 0, tzinfo=timezone.utc),
        miss_distance_km=2.5,
        relative_velocity_kms=7.1,
        pc=1.2e-05,
        sigma_km=0.5,
    )
    assert "CCSDS_CDM_VERS = 1.0" in text
    assert "TCA =" in text
    assert "MISS_DISTANCE =" in text
    assert "COLLISION_PROBABILITY =" in text
    assert "SAT1_CR_R =" in text
    assert "SAT2_CR_R =" in text
    assert "ORIGINATOR = CAS" in text


def test_cdm_public_to_kvn_includes_ids():
    record = CdmPublicRecord(
        cdm_id="999",
        tca=datetime(2026, 6, 30, 12, 0, 0, tzinfo=timezone.utc),
        pc=1e-4,
        min_range_km=3.0,
        sat1_id=25544,
        sat2_id=12345,
        sat1_name="ISS",
        sat2_name="DEB",
        emergency_reportable=True,
    )
    text = cdm_public_to_kvn(record)
    assert "25544" in text
    assert "12345" in text
    assert "CDM_ID 999" in text
