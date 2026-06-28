"""Advanced Pc: Monte Carlo and Alfriend in encounter plane."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backend.app.services.encounter_plane import ensure_positive_definite
from backend.app.services.pc_calculator import DEFAULT_COMBINED_RADIUS_KM, foster_pc

MC_SAMPLES = 10_000
MC_SEED = 42
ALFRIEND_N_R = 150
ALFRIEND_N_THETA = 240


@dataclass(frozen=True)
class EncounterPcResult:
    foster: float
    alfriend: float
    monte_carlo: float
    b_scalar_km: float
    sigma_equiv_km: float


def _as_2d(b_2d: np.ndarray) -> np.ndarray:
    b = np.asarray(b_2d, dtype=float).reshape(2)
    return b


def _as_cov(c_2x2: np.ndarray) -> np.ndarray:
    c = np.asarray(c_2x2, dtype=float).reshape(2, 2)
    return ensure_positive_definite(c)


def foster_from_encounter(b_2d: np.ndarray, c_2x2: np.ndarray, r_km: float) -> tuple[float, float, float]:
    """Isotropic Foster approximation from 2x2 encounter covariance."""
    b = _as_2d(b_2d)
    c = _as_cov(c_2x2)
    b_scalar = float(np.linalg.norm(b))
    sigma_equiv = float(np.sqrt(max(np.trace(c) / 2.0, 1e-12)))
    pc = foster_pc(b_scalar, sigma_equiv, r_km)
    return pc, b_scalar, sigma_equiv


def monte_carlo_pc(
    b_2d: np.ndarray,
    c_2x2: np.ndarray,
    r_km: float,
    n_samples: int = MC_SAMPLES,
    seed: int = MC_SEED,
) -> float:
    """Estimate Pc by sampling 2D Gaussian miss offset in encounter plane."""
    if r_km <= 0:
        raise ValueError("hard body radius must be positive")
    b = _as_2d(b_2d)
    c = _as_cov(c_2x2)
    rng = np.random.default_rng(seed)
    samples = rng.multivariate_normal(b, c, size=n_samples)
    dist = np.linalg.norm(samples, axis=1)
    pc = float(np.mean(dist < r_km))
    return min(max(pc, 0.0), 1.0)


def alfriend_pc(
    b_2d: np.ndarray,
    c_2x2: np.ndarray,
    r_km: float,
    n_r: int = ALFRIEND_N_R,
    n_theta: int = ALFRIEND_N_THETA,
) -> float:
    """
    Numerical integration of 2D Gaussian over circular hard body (numpy only).

    Alfriend-style encounter-plane Pc without scipy.
    """
    if r_km <= 0:
        raise ValueError("hard body radius must be positive")
    b = _as_2d(b_2d)
    c = _as_cov(c_2x2)
    det_c = float(np.linalg.det(c))
    if det_c <= 0:
        return 0.0
    inv_c = np.linalg.inv(c)
    norm = 1.0 / (2.0 * np.pi * np.sqrt(det_c))

    pc = 0.0
    for i in range(n_r):
        r = r_km * (i + 0.5) / n_r
        dr = r_km / n_r
        for j in range(n_theta):
            theta = 2.0 * np.pi * (j + 0.5) / n_theta
            x = np.array([r * np.cos(theta), r * np.sin(theta)])
            dtheta = 2.0 * np.pi / n_theta
            darea = r * dr * dtheta
            diff = x - b
            expo = -0.5 * float(diff @ inv_c @ diff)
            pc += norm * np.exp(expo) * darea
    return min(max(float(pc), 0.0), 1.0)


def pc_from_encounter(
    b_2d: np.ndarray,
    c_2x2: np.ndarray,
    r_km: float = DEFAULT_COMBINED_RADIUS_KM,
) -> EncounterPcResult:
    """Compute Foster, Alfriend, and Monte Carlo Pc from encounter plane state."""
    foster, b_scalar, sigma_equiv = foster_from_encounter(b_2d, c_2x2, r_km)
    alfriend = alfriend_pc(b_2d, c_2x2, r_km)
    mc = monte_carlo_pc(b_2d, c_2x2, r_km)
    return EncounterPcResult(
        foster=foster,
        alfriend=alfriend,
        monte_carlo=mc,
        b_scalar_km=b_scalar,
        sigma_equiv_km=sigma_equiv,
    )
