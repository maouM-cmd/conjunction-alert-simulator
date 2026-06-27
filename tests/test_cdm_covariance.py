"""Tests for CDM RTN covariance and sigma estimation."""

from pathlib import Path

import pytest

from backend.app.services.cdm_covariance import (
    CdmCovariance,
    RtnVariance,
    parse_cdm_covariance,
    sigma_from_cdm_rtn,
)
from backend.app.services.cdm_parser import parse_cdm

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def test_parse_example_cdm_covariance():
    text = (SAMPLES / "example.cdm").read_text(encoding="utf-8")
    record = parse_cdm(text)
    assert record.covariance is not None
    cov = record.covariance
    assert cov.sat1.cr_r == pytest.approx(0.0025)
    assert cov.sat1.ct_t == pytest.approx(0.0040)
    assert cov.sat2.cn_n == pytest.approx(0.0022)


def test_sigma_from_cdm_rtn():
    cov = CdmCovariance(
        sat1=RtnVariance(cr_r=0.0025, ct_t=0.0040, cn_n=0.0018),
        sat2=RtnVariance(cr_r=0.0030, ct_t=0.0055, cn_n=0.0022),
    )
    sigma = sigma_from_cdm_rtn(cov)
    assert sigma is not None
    assert 0.1 <= sigma <= 2.0


def test_sigma_from_empty_covariance():
    cov = CdmCovariance(sat1=RtnVariance(), sat2=RtnVariance())
    assert sigma_from_cdm_rtn(cov) is None


def test_parse_cdm_covariance_none_when_missing():
    fields = {"TCA": "2026/180/00:00:00.000"}
    assert parse_cdm_covariance(fields) is None
