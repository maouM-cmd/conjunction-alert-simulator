"""Tests for Space-Track CDM fetcher."""

import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from backend.app.services.spacetrack_cdm_fetcher import (
    CdmPublicRecord,
    _parse_record,
    _parse_tca,
    _records_from_json,
    fetch_cdm_public,
)

SAMPLE_JSON = [
    {
        "CDM_ID": "123456",
        "TCA": "2026-06-30 12:00:00.0000000",
        "PC": "1.2e-05",
        "MIN_RNG": "2.5",
        "SAT_1_ID": "25544",
        "SAT_2_ID": "99999",
        "SAT_1_NAME": "ISS (ZARYA)",
        "SAT_2_NAME": "TEST DEB",
        "EMERGENCY_REPORTABLE": "N",
    }
]


def test_parse_tca_space_track_format():
    tca = _parse_tca("2026-06-30 12:00:00.0000000")
    assert tca == datetime(2026, 6, 30, 12, 0, 0, tzinfo=timezone.utc)


def test_parse_record_from_json():
    record = _parse_record(SAMPLE_JSON[0])
    assert record is not None
    assert record.cdm_id == "123456"
    assert record.sat1_id == 25544
    assert record.sat2_id == 99999
    assert record.pc == pytest.approx(1.2e-05)
    assert record.min_range_km == pytest.approx(2.5)
    assert record.emergency_reportable is False


def test_records_from_json_skips_invalid():
    records = _records_from_json([{"SAT_1_ID": "0", "SAT_2_ID": "0"}, SAMPLE_JSON[0]])
    assert len(records) == 1


@patch("backend.app.services.spacetrack_cdm_fetcher.spacetrack_client.has_spacetrack_credentials", return_value=True)
@patch("backend.app.services.spacetrack_cdm_fetcher.spacetrack_client.get_json", return_value=SAMPLE_JSON)
def test_fetch_cdm_public_returns_records(_mock_get, _mock_creds, tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    monkeypatch.setattr(
        "backend.app.services.spacetrack_cdm_fetcher.CACHE_DIR",
        cache_dir,
    )
    result = fetch_cdm_public(norad_id=25544, limit=10, force_refresh=True)
    assert len(result.records) == 1
    assert result.records[0].sat1_name == "ISS (ZARYA)"
    assert result.cached is False


@patch("backend.app.services.spacetrack_cdm_fetcher.spacetrack_client.has_spacetrack_credentials", return_value=False)
def test_fetch_without_credentials_raises(_mock_creds):
    with pytest.raises(RuntimeError, match="credentials"):
        fetch_cdm_public(norad_id=25544)
