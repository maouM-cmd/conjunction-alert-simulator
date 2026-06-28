"""Tests for CDM alert compare with Space-Track RTN enrichment (Phase 7A)."""

from datetime import datetime, timezone
from unittest.mock import patch

from backend.app.services.cdm_alert_compare import compare_cdm_alert
from backend.app.services.cdm_types import RtnVariance
from backend.app.services.spacetrack_cdm_fetcher import CdmPublicRecord

SAMPLES = __import__("pathlib").Path(__file__).resolve().parents[1] / "samples"
DEMO_SAT = (SAMPLES / "demo-satellite.tle").read_text(encoding="utf-8").strip()
DEMO_DEB = (SAMPLES / "demo-debris.tle").read_text(encoding="utf-8").strip()
EXAMPLE_CDM = (SAMPLES / "example.cdm").read_text(encoding="utf-8").strip()


def _record_without_rtn() -> CdmPublicRecord:
    return CdmPublicRecord(
        cdm_id="123456",
        tca=datetime(2026, 6, 30, 12, 0, 0, tzinfo=timezone.utc),
        pc=1.2e-05,
        min_range_km=2.5,
        sat1_id=25544,
        sat2_id=35602,
        sat1_name="ISS (ZARYA)",
        sat2_name="COSMOS 2251 DEB",
        emergency_reportable=False,
    )


def _record_with_rtn() -> CdmPublicRecord:
    return CdmPublicRecord(
        cdm_id="123456",
        tca=datetime(2026, 6, 30, 12, 0, 0, tzinfo=timezone.utc),
        pc=8.538007e-06,
        min_range_km=102.3,
        sat1_id=25544,
        sat2_id=35602,
        sat1_name="ISS (ZARYA)",
        sat2_name="COSMOS 2251 DEB",
        emergency_reportable=False,
        relative_speed_kms=12.8079,
        sat1_rtn=RtnVariance(cr_r=0.0025, ct_t=0.004, cn_n=0.0018, cr_t=0.0003, cr_n=0.0002, ct_n=0.0004),
        sat2_rtn=RtnVariance(cr_r=0.003, ct_t=0.0055, cn_n=0.0022),
    )


@patch("backend.app.services.cdm_alert_compare.find_tle_by_norad_id")
@patch("backend.app.services.cdm_alert_compare.enrich_record_with_rtn")
def test_compare_cdm_alert_uses_cdm_covariance(mock_enrich, mock_find_tle):
    from backend.app.services.tle_parser import parse_tle

    mock_find_tle.return_value = parse_tle(DEMO_DEB)
    mock_enrich.return_value = _record_with_rtn()

    result, _ = compare_cdm_alert(DEMO_SAT, _record_without_rtn())
    assert result.sigma_source == "cdm_covariance"
    mock_enrich.assert_called_once()
