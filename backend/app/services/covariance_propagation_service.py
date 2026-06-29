"""TLE RTN covariance propagation from epoch to target time (Phase 10K)."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from backend.app.services.cdm_types import RtnVariance
from backend.app.services.pc_calculator import SIGMA_MIN_KM, tle_epoch_utc
from backend.app.services.tle_parser import ParsedTle
from backend.app.services.tle_rtn_covariance import RTN_N_SCALE, RTN_R_SCALE, RTN_T_SCALE


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        return max(float(raw), 0.0)
    except ValueError:
        return default


def cov_propagation_enabled() -> bool:
    return _env_bool("COV_PROPAGATION_ENABLED", default=False)


def propagation_growth_rates() -> tuple[float, float, float]:
    return (
        _env_float("COV_PROP_R_GROWTH_PER_DAY", 0.10),
        _env_float("COV_PROP_T_GROWTH_PER_DAY", 0.05),
        _env_float("COV_PROP_N_GROWTH_PER_DAY", 0.05),
    )


def delta_days_from_epoch(parsed: ParsedTle, target: datetime) -> float:
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    else:
        target = target.astimezone(timezone.utc)
    epoch = tle_epoch_utc(parsed)
    return abs((target - epoch).total_seconds()) / 86400.0


def anisotropic_covariance_source() -> str:
    if cov_propagation_enabled():
        return "tle_rtn_propagated"
    return "tle_rtn_anisotropic"


def propagate_rtn_variance(
    parsed: ParsedTle,
    target_time: datetime,
    sigma_km: float | None = None,
) -> RtnVariance:
    """Propagate diagonal RTN variance from TLE epoch to target time."""
    sigma0 = SIGMA_MIN_KM if sigma_km is None else sigma_km
    delta_days = delta_days_from_epoch(parsed, target_time)
    k_r, k_t, k_n = propagation_growth_rates()

    sigma_r = sigma0 * RTN_R_SCALE + k_r * delta_days
    sigma_t = sigma0 * RTN_T_SCALE + k_t * delta_days
    sigma_n = sigma0 * RTN_N_SCALE + k_n * delta_days

    return RtnVariance(
        cr_r=sigma_r * sigma_r,
        ct_t=sigma_t * sigma_t,
        cn_n=sigma_n * sigma_n,
    )
