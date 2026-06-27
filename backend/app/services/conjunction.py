"""Conjunction detection and risk assessment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np

from backend.app.services.propagator import OrbitPoint, positions_array, velocities_array


@dataclass(frozen=True)
class ClosestApproach:
    tca: datetime
    miss_distance_km: float
    relative_velocity_kms: float
    index: int


@dataclass(frozen=True)
class ConjunctionEvent:
    debris_norad_id: int
    debris_name: str
    debris_tle: str
    tca: datetime
    miss_distance_km: float
    relative_velocity_kms: float
    risk_level: str


def find_closest_approach(
    primary: list[OrbitPoint],
    secondary: list[OrbitPoint],
) -> ClosestApproach:
    n = min(len(primary), len(secondary))
    if n == 0:
        raise ValueError("軌道点が空です。")

    p_pos = positions_array(primary[:n])
    s_pos = positions_array(secondary[:n])
    diff = p_pos - s_pos
    dist = np.linalg.norm(diff, axis=1)

    idx = int(np.argmin(dist))
    p_vel = velocities_array(primary[:n])[idx]
    s_vel = velocities_array(secondary[:n])[idx]
    rel_vel = float(np.linalg.norm(p_vel - s_vel))

    return ClosestApproach(
        tca=primary[idx].time,
        miss_distance_km=float(dist[idx]),
        relative_velocity_kms=rel_vel,
        index=idx,
    )


def risk_level_from_distance(miss_km: float, threshold_km: float) -> str:
    if miss_km >= threshold_km:
        return "none"
    if miss_km < 1.0:
        return "high"
    if miss_km < 3.0:
        return "medium"
    return "low"


def detect_conjunctions(
    satellite_points: list[OrbitPoint],
    debris_catalog: list[tuple[int, str, str, list[OrbitPoint]]],
    threshold_km: float,
) -> list[ConjunctionEvent]:
    events: list[ConjunctionEvent] = []
    for norad_id, name, tle_text, deb_points in debris_catalog:
        try:
            ca = find_closest_approach(satellite_points, deb_points)
        except ValueError:
            continue
        if ca.miss_distance_km <= threshold_km:
            events.append(
                ConjunctionEvent(
                    debris_norad_id=norad_id,
                    debris_name=name,
                    debris_tle=tle_text,
                    tca=ca.tca,
                    miss_distance_km=ca.miss_distance_km,
                    relative_velocity_kms=ca.relative_velocity_kms,
                    risk_level=risk_level_from_distance(ca.miss_distance_km, threshold_km),
                )
            )
    events.sort(key=lambda e: e.miss_distance_km)
    return events
