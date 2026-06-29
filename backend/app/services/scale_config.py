"""Scale-out configuration (Phase 9D)."""

from __future__ import annotations

import os

DEFAULT_FLEET_MAX_SATELLITES = 10_000
DEFAULT_SCREENING_CHUNK_SIZE = 50
DEFAULT_SCREENING_MAX_WORKERS = 2


def fleet_max_satellites() -> int:
    raw = os.getenv("FLEET_MAX_SATELLITES", "").strip()
    if not raw:
        return DEFAULT_FLEET_MAX_SATELLITES
    try:
        return max(int(raw), 1)
    except ValueError:
        return DEFAULT_FLEET_MAX_SATELLITES


def screening_chunk_size() -> int:
    raw = os.getenv("SCREENING_CHUNK_SIZE", "").strip()
    if not raw:
        return DEFAULT_SCREENING_CHUNK_SIZE
    try:
        return max(int(raw), 1)
    except ValueError:
        return DEFAULT_SCREENING_CHUNK_SIZE


def screening_max_workers() -> int | None:
    raw = os.getenv("SCREENING_MAX_WORKERS", "").strip()
    if not raw:
        raw = os.getenv("BATCH_MAX_WORKERS", "").strip()
    if not raw:
        return None
    try:
        return max(int(raw), 1)
    except ValueError:
        return None
