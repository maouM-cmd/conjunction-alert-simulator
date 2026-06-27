"""CelesTrak + Space-Track unified debris catalog fetcher."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

from backend.app.services.tle_parser import ParsedTle, parse_tle_catalog

CELESTRAK_DEBRIS_URLS = [
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=iridium-33-debris&FORMAT=tle",
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=cosmos-2251-debris&FORMAT=tle",
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=cosmos-1408-debris&FORMAT=tle",
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=fengyun-1c-debris&FORMAT=tle",
]
CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "cache"
CELESTRAK_CACHE_FILE = CACHE_DIR / "debris_catalog.tle"
CELESTRAK_CACHE_META = CACHE_DIR / "debris_catalog.meta"
TTL_SECONDS = 24 * 3600


@dataclass(frozen=True)
class CatalogMeta:
    provider: str
    degraded: bool
    fallback: bool


def _ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _celestrak_cache_age_hours() -> float | None:
    if not CELESTRAK_CACHE_META.exists():
        return None
    try:
        fetched_at = float(CELESTRAK_CACHE_META.read_text(encoding="utf-8").strip())
        return (time.time() - fetched_at) / 3600.0
    except ValueError:
        return None


def is_cache_stale() -> bool:
    age = _celestrak_cache_age_hours()
    if age is None:
        return True
    return age * 3600 > TTL_SECONDS


def cache_age_hours() -> float | None:
    return _celestrak_cache_age_hours()


def _write_celestrak_cache(text: str) -> None:
    _ensure_cache_dir()
    CELESTRAK_CACHE_FILE.write_text(text, encoding="utf-8")
    CELESTRAK_CACHE_META.write_text(str(time.time()), encoding="utf-8")


def _fetch_celestrak_remote() -> str:
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
        raise RuntimeError("CelesTrak returned no valid debris TLE")
    return "\n".join(chunks)


def _dedupe(entries: list[ParsedTle]) -> list[ParsedTle]:
    seen: set[int] = set()
    unique: list[ParsedTle] = []
    for entry in entries:
        if entry.norad_id in seen:
            continue
        seen.add(entry.norad_id)
        unique.append(entry)
    return unique


def _fetch_celestrak(force_refresh: bool = False) -> tuple[list[ParsedTle], bool]:
    degraded = False
    if not force_refresh and CELESTRAK_CACHE_FILE.exists() and not is_cache_stale():
        text = CELESTRAK_CACHE_FILE.read_text(encoding="utf-8")
        entries = _dedupe(parse_tle_catalog(text))
        if entries:
            return entries, degraded
    try:
        text = _fetch_celestrak_remote()
        _write_celestrak_cache(text)
        return _dedupe(parse_tle_catalog(text)), degraded
    except (httpx.HTTPError, RuntimeError):
        if CELESTRAK_CACHE_FILE.exists():
            degraded = True
            text = CELESTRAK_CACHE_FILE.read_text(encoding="utf-8")
            entries = _dedupe(parse_tle_catalog(text))
            if entries:
                return entries, degraded
        raise RuntimeError("CelesTrak fetch failed and no cache available") from None


def get_configured_provider() -> str:
    return os.getenv("TLE_PROVIDER", "celestrak").lower()


def fetch_debris_catalog(force_refresh: bool = False) -> tuple[list[ParsedTle], CatalogMeta]:
    provider = get_configured_provider()

    if provider == "spacetrack":
        from backend.app.services import spacetrack_fetcher

        if spacetrack_fetcher.has_spacetrack_credentials():
            try:
                entries = spacetrack_fetcher.fetch_debris_catalog(force_refresh=force_refresh)
                return entries, CatalogMeta(provider="spacetrack", degraded=False, fallback=False)
            except (RuntimeError, httpx.HTTPError):
                entries, degraded = _fetch_celestrak(force_refresh=force_refresh)
                return entries, CatalogMeta(
                    provider="celestrak (fallback)",
                    degraded=degraded,
                    fallback=True,
                )
        entries, degraded = _fetch_celestrak(force_refresh=force_refresh)
        return entries, CatalogMeta(
            provider="celestrak (no spacetrack creds)",
            degraded=degraded,
            fallback=False,
        )

    entries, degraded = _fetch_celestrak(force_refresh=force_refresh)
    return entries, CatalogMeta(provider="celestrak", degraded=degraded, fallback=False)


def catalog_fetched_at() -> datetime | None:
    if not CELESTRAK_CACHE_META.exists():
        return None
    try:
        ts = float(CELESTRAK_CACHE_META.read_text(encoding="utf-8").strip())
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except ValueError:
        return None


def get_active_provider_label() -> str:
    """Last-known provider label for health endpoint."""
    meta_provider = os.getenv("_CAS_LAST_PROVIDER")
    if meta_provider:
        return meta_provider
    return get_configured_provider()


def set_last_provider_label(label: str) -> None:
    os.environ["_CAS_LAST_PROVIDER"] = label
