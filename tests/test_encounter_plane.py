"""Tests for encounter plane covariance projection."""

import numpy as np
import pytest

from backend.app.services.cdm_types import CdmCovariance, RtnVariance
from backend.app.services.encounter_plane import (
    encounter_covariance_from_cdm,
    encounter_frame_rotation,
    ensure_positive_definite,
    miss_vector_encounter,
    project_covariance_to_encounter,
    rtn_variance_to_matrix,
    rtn_to_teme_rotation,
)


def test_rtn_variance_to_matrix_symmetric():
    rtn = RtnVariance(cr_r=1.0, ct_t=2.0, cn_n=3.0, cr_t=0.1, cr_n=0.2, ct_n=0.3)
    m = rtn_variance_to_matrix(rtn)
    assert m.shape == (3, 3)
    np.testing.assert_allclose(m, m.T)


def test_encounter_frame_orthonormal():
    r_rel = np.array([100.0, 0.0, 0.0])
    v_rel = np.array([0.0, 7.0, 1.0])
    r = encounter_frame_rotation(r_rel, v_rel)
    assert r.shape == (3, 3)
    np.testing.assert_allclose(r.T @ r, np.eye(3), atol=1e-9)


def test_project_covariance_positive_definite():
    r1 = np.array([7000.0, 0.0, 0.0])
    v1 = np.array([0.0, 7.5, 0.0])
    r2 = np.array([7010.0, 5.0, 0.0])
    v2 = np.array([0.0, 7.4, 0.1])
    r_rel = r2 - r1
    v_rel = v2 - v1
    c1 = np.diag([0.01, 0.02, 0.015])
    c2 = np.diag([0.012, 0.018, 0.02])
    r1_teme = rtn_to_teme_rotation(r1, v1)
    r2_teme = rtn_to_teme_rotation(r2, v2)
    c1_teme = r1_teme @ c1 @ r1_teme.T
    c2_teme = r2_teme @ c2 @ r2_teme.T
    r_enc = encounter_frame_rotation(r_rel, v_rel)
    c_2x2 = project_covariance_to_encounter(c1_teme, c2_teme, r_enc)
    c_2x2 = ensure_positive_definite(c_2x2)
    evals = np.linalg.eigvalsh(c_2x2)
    assert np.all(evals > 0)


def test_encounter_covariance_from_cdm():
    cov = CdmCovariance(
        sat1=RtnVariance(cr_r=0.0025, ct_t=0.0040, cn_n=0.0018),
        sat2=RtnVariance(cr_r=0.0030, ct_t=0.0055, cn_n=0.0022),
    )
    r1 = np.array([6778.0, 100.0, 50.0])
    v1 = np.array([-1.0, 7.5, 0.2])
    r2 = np.array([6780.0, 120.0, 55.0])
    v2 = np.array([-0.8, 7.3, 0.3])
    r_rel = r2 - r1
    v_rel = v2 - v1
    result = encounter_covariance_from_cdm(cov, r1, v1, r2, v2, r_rel, v_rel)
    assert result is not None
    c_2x2, b_2d = result
    assert c_2x2.shape == (2, 2)
    assert b_2d.shape == (2,)
    assert np.linalg.norm(b_2d) >= 0


def test_miss_vector_encounter_dimension():
    r_rel = np.array([30.0, 1.0, 2.0])
    v_rel = np.array([0.0, 7.0, 0.5])
    r_enc = encounter_frame_rotation(r_rel, v_rel)
    b = miss_vector_encounter(r_rel, r_enc)
    assert len(b) == 2
