"""CelesTrak debris TLE fetcher with file cache."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from backend.app.services.tle_parser import ParsedTle, parse_tle_catalog

# CelesTrak removed GROUP=debris; merge known collision-debris groups instead.
CELESTRAK_DEBRIS_URLS = [
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=iridium-33-debris&FORMAT=tle",
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=cosmos-2251-debris&FORMAT=tle",
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=cosmos-1408-debris&FORMAT=tle",
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=fengyun-1c-debris&FORMAT=tle",
]
CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "cache"
CACHE_FILE = CACHE_DIR / "debris_catalog.tle"
CACHE_META = CACHE_DIR / "debris_catalog.meta"
TTL_SECONDS = 24 * 3600


def _ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


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


def _write_cache(text: str) -> None:
    _ensure_cache_dir()
    CACHE_FILE.write_text(text, encoding="utf-8")
    CACHE_META.write_text(str(time.time()), encoding="utf-8")


def _fetch_remote_catalog() -> str:
    chunks: list[str] = []
    with httpx.Client(timeout=90.0, follow_redirects=True) as client:
        for url in CELESTRAK_DEBRIS_URLS:
            response = client.get(url)
            response.raise_for_status()
            text = response.text.strip()
            if not text or text.startswith("Invalid query"):
                continue
            chunks.append(text)
    if not chunks:
        raise RuntimeError("CelesTrakから有効なデブリTLEを取得できませんでした。")
    return "\n".join(chunks)


def _dedupe_catalog(entries: list[ParsedTle]) -> list[ParsedTle]:
    seen: set[int] = set()
    unique: list[ParsedTle] = []
    for entry in entries:
        if entry.norad_id in seen:
            continue
        seen.add(entry.norad_id)
        unique.append(entry)
    return unique


def fetch_debris_catalog(force_refresh: bool = False) -> tuple[list[ParsedTle], bool]:
    """Return debris TLE list and whether cache is degraded (stale fetch fallback)."""
    degraded = False

    if not force_refresh and CACHE_FILE.exists() and not is_cache_stale():
        text = CACHE_FILE.read_text(encoding="utf-8")
        entries = _dedupe_catalog(parse_tle_catalog(text))
        if entries:
            return entries, degraded

    try:
        text = _fetch_remote_catalog()
        _write_cache(text)
        return _dedupe_catalog(parse_tle_catalog(text)), degraded
    except (httpx.HTTPError, RuntimeError):
        if CACHE_FILE.exists():
            degraded = True
            text = CACHE_FILE.read_text(encoding="utf-8")
            entries = _dedupe_catalog(parse_tle_catalog(text))
            if entries:
                return entries, degraded
        raise RuntimeError("CelesTrakからTLEを取得できず、キャッシュもありません。") from None


def catalog_fetched_at() -> datetime | None:
    if not CACHE_META.exists():
        return None
    try:
        ts = float(CACHE_META.read_text(encoding="utf-8").strip())
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except ValueError:
        return None
