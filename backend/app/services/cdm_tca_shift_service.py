"""CDM encounter covariance evaluation at CDM TCA (Phase 10M)."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import numpy as np

from backend.app.services.cdm_parser import CdmRecord
from backend.app.services.propagator import OrbitPoint


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def cdm_tca_shift_enabled() -> bool:
    return _env_bool("CDM_TCA_SHIFT_ENABLED", default=False)


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def index_nearest_tca(
    sat_pts: list[OrbitPoint],
    deb_pts: list[OrbitPoint],
    target_tca: datetime,
) -> int:
    """Return grid index whose time is closest to target_tca on both tracks."""
    target = _ensure_aware(target_tca)
    best_idx = 0
    best_delta: float | None = None
    n = min(len(sat_pts), len(deb_pts))
    for i in range(n):
        delta = abs((_ensure_aware(sat_pts[i].time) - target).total_seconds())
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_idx = i
    return best_idx


def _state_at_index(
    points: list[OrbitPoint],
    index: int,
) -> tuple[np.ndarray, np.ndarray]:
    idx = min(index, len(points) - 1)
    p = points[idx]
    return np.array(p.position_km, dtype=float), np.array(p.velocity_kms, dtype=float)


def encounter_states_for_cdm(
    cdm: CdmRecord,
    sat_pts: list[OrbitPoint],
    deb_pts: list[OrbitPoint],
    fallback_index: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, bool]:
    """
    Select orbit states for CDM encounter projection.

    Returns (r1, v1, r2, v2, r_rel, v_rel, eval_index, shift_applied).
    """
    shift_applied = cdm_tca_shift_enabled() and cdm.tca is not None
    if shift_applied:
        eval_index = index_nearest_tca(sat_pts, deb_pts, cdm.tca)
    else:
        eval_index = min(fallback_index, len(sat_pts) - 1, len(deb_pts) - 1)

    r1, v1 = _state_at_index(sat_pts, eval_index)
    r2, v2 = _state_at_index(deb_pts, eval_index)
    r_rel = r2 - r1
    v_rel = v2 - v1
    return r1, v1, r2, v2, r_rel, v_rel, eval_index, shift_applied
