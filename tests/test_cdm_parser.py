"""Tests for CDM parser."""

from pathlib import Path

import pytest

from backend.app.services.cdm_parser import parse_cdm

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def test_parse_example_cdm():
    text = (SAMPLES / "example.cdm").read_text(encoding="utf-8")
    record = parse_cdm(text)
    assert record.tca is not None
    assert record.miss_distance_km == pytest.approx(29.75, rel=1e-3)
    assert record.relative_speed_kms == pytest.approx(7.283, rel=1e-3)
    assert record.pc_external == pytest.approx(3.2e-05, rel=1e-6)
    assert record.sat1_object == "ISS (ZARYA)"
    assert record.sat2_object == "COSMOS 2251 DEB"


def test_parse_empty_raises():
    with pytest.raises(ValueError):
        parse_cdm("# empty\n")
