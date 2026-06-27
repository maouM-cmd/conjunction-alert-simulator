"""CDM RTN position covariance parsing and sigma estimation."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from backend.app.services.pc_calculator import SIGMA_MAX_KM, SIGMA_MIN_KM

_VARIANCE_UNIT = re.compile(r"^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*(\w*)")


@dataclass(frozen=True)
class RtnVariance:
    """RTN position variance (km^2) for one object."""

    cr_r: float | None = None
    ct_t: float | None = None
    cn_n: float | None = None
    cr_t: float | None = None
    cr_n: float | None = None
    ct_n: float | None = None


@dataclass(frozen=True)
class CdmCovariance:
    sat1: RtnVariance
    sat2: RtnVariance


def _parse_variance_km2(value: str) -> float:
    """Parse variance with optional unit (m^2 -> km^2)."""
    match = _VARIANCE_UNIT.match(value.strip())
    if not match:
        raise ValueError(f"分散値を解析できません: {value}")
    number = float(match.group(1))
    unit = match.group(2).lower().replace("^2", "2").replace("²", "2")
    if unit in ("m2", "m**2"):
        return (number / 1000.0) ** 2
    if unit in ("km2", "km**2", ""):
        return number
    return number


def _rtn_from_fields(fields: dict[str, str], prefix: str) -> RtnVariance:
    def get(key: str) -> float | None:
        full = f"{prefix}_{key}"
        if full not in fields:
            return None
        return _parse_variance_km2(fields[full])

    return RtnVariance(
        cr_r=get("CR_R"),
        ct_t=get("CT_T"),
        cn_n=get("CN_N"),
        cr_t=get("CR_T"),
        cr_n=get("CR_N"),
        ct_n=get("CT_N"),
    )


def parse_cdm_covariance(fields: dict[str, str]) -> CdmCovariance | None:
    """Extract RTN covariance from CDM key=value fields."""
    sat1 = _rtn_from_fields(fields, "SAT1")
    sat2 = _rtn_from_fields(fields, "SAT2")
    has_any = any(
        v is not None
        for v in (
            sat1.cr_r,
            sat1.ct_t,
            sat1.cn_n,
            sat2.cr_r,
            sat2.ct_t,
            sat2.cn_n,
        )
    )
    if not has_any:
        return None
    return CdmCovariance(sat1=sat1, sat2=sat2)


def _rtn_sigma_km(rtn: RtnVariance) -> float:
    """RSS of RTN position standard deviations (km)."""
    terms: list[float] = []
    for var in (rtn.cr_r, rtn.ct_t, rtn.cn_n):
        if var is not None and var >= 0:
            terms.append(math.sqrt(var))
    if not terms:
        return 0.0
    return math.sqrt(sum(t * t for t in terms))


def sigma_from_cdm_rtn(cov: CdmCovariance) -> float | None:
    """
    Combined 1-sigma approximation for encounter plane (conservative RSS).

    sigma = sqrt(sigma1^2 + sigma2^2) where each sigma is RSS of RTN std devs.
    """
    s1 = _rtn_sigma_km(cov.sat1)
    s2 = _rtn_sigma_km(cov.sat2)
    if s1 <= 0 and s2 <= 0:
        return None
    combined = math.sqrt(s1 * s1 + s2 * s2)
    return min(max(combined, SIGMA_MIN_KM), SIGMA_MAX_KM)
