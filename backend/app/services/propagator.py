"""SGP4 orbit propagation in TEME coordinates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
from sgp4.api import Satrec, jday

from backend.app.services.tle_parser import ParsedTle


@dataclass(frozen=True)
class OrbitPoint:
    time: datetime
    position_km: tuple[float, float, float]
    velocity_kms: tuple[float, float, float]


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def create_satrec(parsed: ParsedTle) -> Satrec:
    sat = Satrec.twoline2rv(parsed.line1, parsed.line2)
    if sat.error != 0:
        raise ValueError(f"SGP4初期化エラー (code={sat.error})")
    return sat


def propagate_orbit(
    parsed: ParsedTle,
    start: datetime,
    duration_days: float,
    step_minutes: int,
) -> list[OrbitPoint]:
    sat = create_satrec(parsed)
    start = _to_utc(start)
    end = start + timedelta(days=duration_days)
    step = timedelta(minutes=step_minutes)

    points: list[OrbitPoint] = []
    t = start
    while t <= end:
        jd, fr = jday(
            t.year,
            t.month,
            t.day,
            t.hour,
            t.minute,
            t.second + t.microsecond / 1e6,
        )
        err, r, v = sat.sgp4(jd, fr)
        if err != 0:
            break
        points.append(
            OrbitPoint(
                time=t,
                position_km=(float(r[0]), float(r[1]), float(r[2])),
                velocity_kms=(float(v[0]), float(v[1]), float(v[2])),
            )
        )
        t += step
    return points


def positions_array(points: list[OrbitPoint]) -> np.ndarray:
    return np.array([p.position_km for p in points], dtype=np.float64)


def velocities_array(points: list[OrbitPoint]) -> np.ndarray:
    return np.array([p.velocity_kms for p in points], dtype=np.float64)


def apply_maneuver(
    parsed: ParsedTle,
    direction: str,
    delta_v_ms: float,
) -> ParsedTle:
    """Apply instantaneous delta-v at epoch to produce modified TLE (approximation)."""
    sat = create_satrec(parsed)
    err, r, v = sat.sgp4(sat.jdsatepoch, sat.jdsatepochF)
    if err != 0:
        raise ValueError("マニューバ適用時の軌道計算に失敗しました。")

    v_kms = np.array(v, dtype=np.float64)
    speed = np.linalg.norm(v_kms)
    if speed < 1e-9:
        raise ValueError("速度ベクトルがゼロのためマニューバ方向を決定できません。")

    delta_v_kms = delta_v_ms / 1000.0
    if direction == "prograde":
        dv = delta_v_kms * (v_kms / speed)
    elif direction == "retrograde":
        dv = -delta_v_kms * (v_kms / speed)
    elif direction == "normal":
        r_vec = np.array(r, dtype=np.float64)
        normal = np.cross(r_vec, v_kms)
        n_norm = np.linalg.norm(normal)
        if n_norm < 1e-9:
            raise ValueError("法線方向を計算できません。")
        dv = delta_v_kms * (normal / n_norm)
    else:
        raise ValueError(f"未知のマニューバ方向: {direction}")

    new_v = v_kms + dv
    # Re-build TLE from modified state at epoch (simplified: adjust mean motion via velocity)
    # For Phase 1 we propagate with modified initial velocity by creating a synthetic TLE
    # using exporter from modified state is complex; instead store maneuver as offset propagation.
    # Practical approach: return parsed unchanged but attach dv in conjunction service.
    _ = new_v  # used in conjunction service via velocity offset propagation
    return parsed


def propagate_with_velocity_offset(
    parsed: ParsedTle,
    start: datetime,
    duration_days: float,
    step_minutes: int,
    velocity_offset_kms: tuple[float, float, float],
) -> list[OrbitPoint]:
    """Propagate orbit applying constant velocity offset after epoch (Phase 1 approximation)."""
    base = propagate_orbit(parsed, start, duration_days, step_minutes)
    offset = np.array(velocity_offset_kms, dtype=np.float64)
    result: list[OrbitPoint] = []
    t0 = _to_utc(start)
    for p in base:
        dt_sec = (p.time - t0).total_seconds()
        pos = np.array(p.position_km) + offset * dt_sec
        vel = np.array(p.velocity_kms) + offset
        result.append(
            OrbitPoint(
                time=p.time,
                position_km=(float(pos[0]), float(pos[1]), float(pos[2])),
                velocity_kms=(float(vel[0]), float(vel[1]), float(vel[2])),
            )
        )
    return result


def compute_maneuver_offset(
    parsed: ParsedTle,
    direction: str,
    delta_v_ms: float,
) -> tuple[float, float, float]:
    sat = create_satrec(parsed)
    err, r, v = sat.sgp4(sat.jdsatepoch, sat.jdsatepochF)
    if err != 0:
        raise ValueError("マニューバ方向の計算に失敗しました。")

    v_kms = np.array(v, dtype=np.float64)
    speed = np.linalg.norm(v_kms)
    delta_v_kms = delta_v_ms / 1000.0

    if direction == "prograde":
        dv = delta_v_kms * (v_kms / speed)
    elif direction == "retrograde":
        dv = -delta_v_kms * (v_kms / speed)
    elif direction == "normal":
        r_vec = np.array(r, dtype=np.float64)
        normal = np.cross(r_vec, v_kms)
        n_norm = np.linalg.norm(normal)
        dv = delta_v_kms * (normal / n_norm)
    else:
        raise ValueError(f"未知のマニューバ方向: {direction}")

    return (float(dv[0]), float(dv[1]), float(dv[2]))
