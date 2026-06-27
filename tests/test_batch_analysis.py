"""Tests for batch conjunction analysis."""

from unittest.mock import patch

import pytest

from backend.app.services.analysis import ConjunctionAnalysisResult
from backend.app.services.batch_analysis import (
    MAX_SATELLITES,
    parse_multi_tle_block,
    run_batch_conjunction_analysis,
)
from backend.app.services.tle_fetcher import CatalogMeta
from backend.app.services.tle_parser import parse_tle

SAMPLES = __import__("pathlib").Path(__file__).resolve().parents[1] / "samples"

DEMO_SAT = (SAMPLES / "demo-satellite.tle").read_text(encoding="utf-8").strip()
DEMO_DEB = (SAMPLES / "demo-debris.tle").read_text(encoding="utf-8").strip()


def _fake_catalog():
    debris = parse_tle(DEMO_DEB)
    meta = CatalogMeta(provider="test", degraded=False, fallback=False)
    return [debris], meta


def test_parse_multi_tle_block():
    text = (SAMPLES / "constellation-demo.tle").read_text(encoding="utf-8")
    blocks = parse_multi_tle_block(text)
    assert len(blocks) == 6


def test_max_satellites_raises():
    tles = [DEMO_SAT] * (MAX_SATELLITES + 1)
    with pytest.raises(ValueError, match="最大"):
        run_batch_conjunction_analysis(tles, threshold_km=50.0, parallel=False)


@patch("backend.app.services.batch_analysis.fetch_debris_catalog", side_effect=_fake_catalog)
def test_batch_returns_per_satellite(_mock_fetch):
    result = run_batch_conjunction_analysis(
        [DEMO_SAT],
        duration_days=1.0,
        threshold_km=50.0,
        step_minutes=5,
        parallel=False,
    )
    assert result.summary.satellite_count == 1
    assert isinstance(result.results[0], ConjunctionAnalysisResult)
    assert result.tle_provider == "test"
    assert result.parallel is False
    assert result.worker_count == 1


@patch("backend.app.services.batch_analysis.fetch_debris_catalog", side_effect=_fake_catalog)
def test_batch_parallel_preserves_order(_mock_fetch):
    blocks = parse_multi_tle_block(
        (SAMPLES / "constellation-demo.tle").read_text(encoding="utf-8")
    )[:2]
    result = run_batch_conjunction_analysis(
        blocks,
        duration_days=1.0,
        threshold_km=50.0,
        step_minutes=5,
        parallel=False,
    )
    assert len(result.results) == 2
    assert result.results[0].satellite.name == "STARLINK-1007"
    assert result.results[1].satellite.name == "STARLINK-1008"
