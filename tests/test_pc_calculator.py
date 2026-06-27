"""Tests for Foster Pc calculator."""

import math
from datetime import datetime, timezone

import pytest

from backend.app.services.pc_calculator import (
    DEFAULT_COMBINED_RADIUS_KM,
    foster_pc,
    sigma_from_tle_age,
)
from backend.app.services.tle_parser import parse_tle

ISS_TLE = """ISS (ZARYA)
1 25544U 98067A   25179.51782528  .00016717  00000+0  10270-3 0  9993
2 25544  51.6347  74.8662 0004176 315.5599 138.2340 15.50909589423071"""


def test_foster_pc_zero_miss_distance():
    pc = foster_pc(0.0, 1.0, 0.015)
    expected = (0.015**2) / (2 * 1.0**2)
    assert pc == pytest.approx(expected, rel=1e-9)


def test_foster_pc_large_miss_distance():
    pc = foster_pc(100.0, 1.0, 0.015)
    assert pc < 1e-100


def test_foster_pc_sigma_floor():
    pc = foster_pc(1.0, 0.0, 0.015)
    assert pc > 0
    assert pc <= 1.0


def test_foster_pc_clipped_at_one():
    pc = foster_pc(0.0, 0.01, 1.0)
    assert pc == 1.0


def test_sigma_from_tle_age_in_range():
    sat = parse_tle(ISS_TLE)
    analysis = datetime(2026, 6, 28, tzinfo=timezone.utc)
    sigma = sigma_from_tle_age(sat, sat, analysis)
    assert 0.1 <= sigma <= 2.0


def test_invalid_miss_distance():
    with pytest.raises(ValueError):
        foster_pc(-1.0, 1.0, DEFAULT_COMBINED_RADIUS_KM)
