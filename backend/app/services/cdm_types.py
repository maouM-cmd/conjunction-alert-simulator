"""CDM covariance datatypes (no service imports)."""

from __future__ import annotations

from dataclasses import dataclass


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
