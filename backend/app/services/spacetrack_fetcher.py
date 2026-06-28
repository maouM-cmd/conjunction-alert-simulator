"""Space-Track.org TLE fetcher with session auth and file cache."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from backend.app.services import spacetrack_client
from backend.app.services.tle_parser import ParsedTle, parse_tle_catalog

QUERY_URL = (
    "https://www.space-track.org/basicspacedata/query/class/gp/"
    "DECAY_DATE/null-val/"
    "OBJECT_TYPE/Rocket%20Body,DEB/"
    "format/tle"
)
CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "cache"
CACHE_FILE = CACHE_DIR / "spacetrack_debris.tle"
CACHE_META = CACHE_DIR / "spacetrack_debris.meta"
TTL_SECONDS = 24 * 3600


def has_spacetrack_credentials() -> bool:
    return spacetrack_client.has_spacetrack_credentials()


def _ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _write_cache(text: str) -> None:
    _ensure_cache_dir()
    CACHE_FILE.write_text(text, encoding="utf-8")
    CACHE_META.write_text(str(time.time()), encoding="utf-8")


def cache_age_hours() -> float | None:
    if not CACHE_META.exists():
        return None
    try:
        fetched_at = float(CACHE_META.read_text(encoding="utf-8").strip())
        return (time.time() - fetched_at) / 3600.0
    except ValueError:
        return None


def is_cache_stale() -> bool:
    age = cache_age_hours()
    if age is None:
        return True
    return age * 3600 > TTL_SECONDS


def _fetch_remote_catalog() -> str:
    text = spacetrack_client.get_text(QUERY_URL)
    if not text or text.startswith("No GP data found"):
        raise RuntimeError("Space-Track returned empty debris catalog")
    return text


def _dedupe(entries: list[ParsedTle]) -> list[ParsedTle]:
    seen: set[int] = set()
    unique: list[ParsedTle] = []
    for entry in entries:
        if entry.norad_id in seen:
            continue
        seen.add(entry.norad_id)
        unique.append(entry)
    return unique


def fetch_debris_catalog(force_refresh: bool = False) -> list[ParsedTle]:
    if not has_spacetrack_credentials():
        raise RuntimeError("Space-Track credentials not configured")

    if not force_refresh and CACHE_FILE.exists() and not is_cache_stale():
        text = CACHE_FILE.read_text(encoding="utf-8")
        entries = _dedupe(parse_tle_catalog(text))
        if entries:
            return entries

    text = _fetch_remote_catalog()
    _write_cache(text)
    return _dedupe(parse_tle_catalog(text))


def catalog_fetched_at() -> datetime | None:
    if not CACHE_META.exists():
        return None
    try:
        ts = float(CACHE_META.read_text(encoding="utf-8").strip())
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except ValueError:
        return None
