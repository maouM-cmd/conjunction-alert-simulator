"""Encounter plane frame transforms and covariance projection."""

from __future__ import annotations

import numpy as np

from backend.app.services.cdm_types import CdmCovariance, RtnVariance


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if n < 1e-12:
        raise ValueError("零ベクトルから単位ベクトルを作成できません。")
    return v / n


def _cross(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.cross(a, b)


def rtn_variance_to_matrix(rtn: RtnVariance) -> np.ndarray:
    """Build symmetric 3x3 RTN covariance matrix (km^2)."""
    cr_r = rtn.cr_r if rtn.cr_r is not None else 0.0
    ct_t = rtn.ct_t if rtn.ct_t is not None else 0.0
    cn_n = rtn.cn_n if rtn.cn_n is not None else 0.0
    cr_t = rtn.cr_t if rtn.cr_t is not None else 0.0
    cr_n = rtn.cr_n if rtn.cr_n is not None else 0.0
    ct_n = rtn.ct_n if rtn.ct_n is not None else 0.0
    return np.array(
        [
            [cr_r, cr_t, cr_n],
            [cr_t, ct_t, ct_n],
            [cr_n, ct_n, cn_n],
        ],
        dtype=float,
    )


def rtn_to_teme_rotation(r: np.ndarray, v: np.ndarray) -> np.ndarray:
    """
    Rotation matrix R where columns are RTN basis vectors in TEME.

    r_teme = R @ r_rtn
    """
    r_hat = _unit(r)
    h = _cross(r, v)
    n_hat = _unit(h)
    t_hat = _cross(n_hat, r_hat)
    return np.column_stack([r_hat, t_hat, n_hat])


def encounter_frame_rotation(r_rel: np.ndarray, v_rel: np.ndarray) -> np.ndarray:
    """
    Rotation matrix R where columns are encounter basis (x,y,z) in TEME.

    x: along relative velocity, z: along angular momentum, y: completes RH frame.
    """
    x_hat = _unit(v_rel)
    z_hat = _unit(_cross(r_rel, v_rel))
    y_hat = _cross(z_hat, x_hat)
    return np.column_stack([x_hat, y_hat, z_hat])


def teme_covariance_from_rtn(c_rtn: np.ndarray, r: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Transform RTN 3x3 covariance to TEME."""
    r_rtn = rtn_to_teme_rotation(r, v)
    return r_rtn @ c_rtn @ r_rtn.T


def project_covariance_to_encounter(
    cov1_teme: np.ndarray,
    cov2_teme: np.ndarray,
    r_enc: np.ndarray,
) -> np.ndarray:
    """
    Combine independent TEME covariances and project to encounter y-z plane (2x2).

    x axis is along relative velocity; miss plane is y-z.
    """
    c_teme = cov1_teme + cov2_teme
    c_enc = r_enc.T @ c_teme @ r_enc
    return c_enc[1:3, 1:3].copy()


def miss_vector_encounter(r_rel: np.ndarray, r_enc: np.ndarray) -> np.ndarray:
    """Relative position projected to encounter y-z plane (km)."""
    r_enc_vec = r_enc.T @ r_rel
    return r_enc_vec[1:3].copy()


def ensure_positive_definite(c: np.ndarray, floor: float = 1e-10) -> np.ndarray:
    """Regularize 2x2 covariance to be positive definite."""
    c = np.array(c, dtype=float)
    evals, evecs = np.linalg.eigh(c)
    evals = np.maximum(evals, floor)
    return evecs @ np.diag(evals) @ evecs.T


def encounter_covariance_from_cdm(
    cov: CdmCovariance,
    r1: np.ndarray,
    v1: np.ndarray,
    r2: np.ndarray,
    v2: np.ndarray,
    r_rel: np.ndarray,
    v_rel: np.ndarray,
) -> tuple[np.ndarray, np.ndarray] | None:
    """
    Build encounter-plane 2x2 covariance and miss vector from CDM RTN data.

    Returns (C_2x2, b_2d) or None if insufficient covariance data.
    """
    c1 = rtn_variance_to_matrix(cov.sat1)
    c2 = rtn_variance_to_matrix(cov.sat2)
    if np.trace(c1) <= 0 and np.trace(c2) <= 0:
        return None

    cov1_teme = teme_covariance_from_rtn(c1, r1, v1)
    cov2_teme = teme_covariance_from_rtn(c2, r2, v2)
    r_enc = encounter_frame_rotation(r_rel, v_rel)
    c_2x2 = project_covariance_to_encounter(cov1_teme, cov2_teme, r_enc)
    c_2x2 = ensure_positive_definite(c_2x2)
    b_2d = miss_vector_encounter(r_rel, r_enc)
    return c_2x2, b_2d
