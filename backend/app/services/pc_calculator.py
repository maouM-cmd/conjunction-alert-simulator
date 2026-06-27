"""Foster 2D collision probability (Pc) for conjunction events."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from backend.app.services.propagator import create_satrec
from backend.app.services.tle_parser import ParsedTle

# Default hard-body radii (km)
DEFAULT_SATELLITE_RADIUS_KM = 0.010
DEFAULT_DEBRIS_RADIUS_KM = 0.005
DEFAULT_COMBINED_RADIUS_KM = DEFAULT_SATELLITE_RADIUS_KM + DEFAULT_DEBRIS_RADIUS_KM

SIGMA_MIN_KM = 0.1
SIGMA_MAX_KM = 2.0
SIGMA_PER_DAY_KM = 0.05


def foster_pc(miss_km: float, sigma_km: float, hard_body_radius_km: float) -> float:
    """
    Foster 2D circular hard-body model in encounter plane.

    Pc = (R^2 / (2 * sigma^2)) * exp(-b^2 / (2 * sigma^2))
    """
    if miss_km < 0:
        raise ValueError("miss distance must be non-negative")
    if hard_body_radius_km <= 0:
        raise ValueError("hard body radius must be positive")

    sigma = max(sigma_km, SIGMA_MIN_KM)
    b = miss_km
    r = hard_body_radius_km

    exponent = -(b * b) / (2.0 * sigma * sigma)
    pc = (r * r / (2.0 * sigma * sigma)) * math.exp(exponent)
    return min(max(pc, 0.0), 1.0)


def tle_epoch_utc(parsed: ParsedTle) -> datetime:
    sat = create_satrec(parsed)
    jd = sat.jdsatepoch + sat.jdsatepochF
    # Julian date to datetime (UTC)
    a = jd + 0.5
    z = int(a)
    f = a - z
    if z < 2299161:
        b = z
    else:
        alpha = int((z - 1867216.25) / 36524.25)
        b = z + 1 + alpha - int(alpha / 4)
    c = b + 1524
    d = int((c - 122.1) / 365.25)
    e = int(365.25 * d)
    g = int((c - e) / 30.6001)
    day = c - e - int(30.6001 * g) + f
    month = g - 1 if g < 14 else g - 13
    year = d - 4716 if month > 2 else d - 4715
    day_int = int(day)
    day_frac = day - day_int
    hours = day_frac * 24.0
    hour = int(hours)
    minutes = (hours - hour) * 60.0
    minute = int(minutes)
    seconds = (minutes - minute) * 60.0
    return datetime(year, month, day_int, hour, minute, int(seconds), tzinfo=timezone.utc)


def sigma_from_tle_age(
    satellite: ParsedTle,
    debris: ParsedTle,
    analysis_time: datetime,
) -> float:
    """Estimate 1-sigma position uncertainty from TLE epoch age."""
    if analysis_time.tzinfo is None:
        analysis_time = analysis_time.replace(tzinfo=timezone.utc)
    else:
        analysis_time = analysis_time.astimezone(timezone.utc)

    ages_days: list[float] = []
    for parsed in (satellite, debris):
        epoch = tle_epoch_utc(parsed)
        age = abs((analysis_time - epoch).total_seconds()) / 86400.0
        ages_days.append(age)

    max_age = max(ages_days)
    sigma = SIGMA_MIN_KM + SIGMA_PER_DAY_KM * max_age
    return min(max(sigma, SIGMA_MIN_KM), SIGMA_MAX_KM)


def compute_pc_for_conjunction(
    miss_km: float,
    satellite: ParsedTle,
    debris: ParsedTle,
    analysis_time: datetime,
    sigma_km: float | None = None,
    hard_body_radius_km: float = DEFAULT_COMBINED_RADIUS_KM,
) -> float:
    if sigma_km is None:
        sigma_km = sigma_from_tle_age(satellite, debris, analysis_time)
    return foster_pc(miss_km, sigma_km, hard_body_radius_km)
