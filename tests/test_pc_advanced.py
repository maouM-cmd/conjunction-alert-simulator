"""Tests for Monte Carlo and Alfriend Pc."""

import numpy as np
import pytest

from backend.app.services.pc_advanced import (
    MC_SAMPLES,
    alfriend_pc,
    foster_from_encounter,
    monte_carlo_pc,
    pc_from_encounter,
)
from backend.app.services.pc_calculator import DEFAULT_COMBINED_RADIUS_KM, foster_pc


def test_foster_from_encounter_matches_scalar():
    b = np.array([0.0, 0.0])
    c = np.diag([1.0, 1.0])
    pc, b_scalar, sigma = foster_from_encounter(b, c, DEFAULT_COMBINED_RADIUS_KM)
    expected = foster_pc(0.0, 1.0, DEFAULT_COMBINED_RADIUS_KM)
    assert b_scalar == pytest.approx(0.0)
    assert sigma == pytest.approx(1.0)
    assert pc == pytest.approx(expected, rel=1e-9)


def test_monte_carlo_near_foster_at_origin():
    b = np.array([0.0, 0.0])
    c = np.diag([0.5, 0.5])
    foster, _, _ = foster_from_encounter(b, c, DEFAULT_COMBINED_RADIUS_KM)
    mc = monte_carlo_pc(b, c, DEFAULT_COMBINED_RADIUS_KM, n_samples=MC_SAMPLES, seed=42)
    assert mc == pytest.approx(foster, rel=0.4)


def test_alfriend_near_monte_carlo():
    b = np.array([0.02, 0.01])
    c = np.diag([0.05, 0.05])
    mc = monte_carlo_pc(b, c, DEFAULT_COMBINED_RADIUS_KM, n_samples=MC_SAMPLES, seed=7)
    alf = alfriend_pc(b, c, DEFAULT_COMBINED_RADIUS_KM)
    assert alf == pytest.approx(mc, rel=0.2)
    assert alf > 0
    assert mc > 0


def test_large_miss_distance_pc_near_zero():
    b = np.array([50.0, 40.0])
    c = np.diag([0.1, 0.1])
    result = pc_from_encounter(b, c, DEFAULT_COMBINED_RADIUS_KM)
    assert result.foster < 1e-20
    assert result.alfriend < 1e-10
    assert result.monte_carlo < 0.01


def test_pc_from_encounter_returns_all_methods():
    b = np.array([0.5, 0.2])
    c = np.diag([0.2, 0.25])
    result = pc_from_encounter(b, c, DEFAULT_COMBINED_RADIUS_KM)
    assert 0.0 <= result.foster <= 1.0
    assert 0.0 <= result.alfriend <= 1.0
    assert 0.0 <= result.monte_carlo <= 1.0
