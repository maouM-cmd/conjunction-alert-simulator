"""Space-Track cdm_public fetcher with file cache."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.app.services import spacetrack_client

CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "cache"
TTL_SECONDS = 24 * 3600


@dataclass(frozen=True)
class CdmPublicRecord:
    cdm_id: str
    tca: datetime | None
    pc: float | None
    min_range_km: float | None
    sat1_id: int
    sat2_id: int
    sat1_name: str | None
    sat2_name: str | None
    emergency_reportable: bool | None


@dataclass(frozen=True)
class CdmFetchResult:
    records: list[CdmPublicRecord]
    cached: bool
    degraded: bool


def _ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_paths(norad_id: int | None) -> tuple[Path, Path]:
    key = norad_id if norad_id is not None else 0
    return (
        CACHE_DIR / f"spacetrack_cdm_{key}.json",
        CACHE_DIR / f"spacetrack_cdm_{key}.meta",
    )


def _is_cache_stale(meta_path: Path) -> bool:
    if not meta_path.exists():
        return True
    try:
        fetched_at = float(meta_path.read_text(encoding="utf-8").strip())
        return (time.time() - fetched_at) > TTL_SECONDS
    except ValueError:
        return True


def _parse_tca(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    text = text.replace("T", " ")
    if "." in text:
        head, frac = text.rsplit(".", 1)
        frac = frac[:6].ljust(6, "0")
        text = f"{head}.{frac}"
    try:
        return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_record(raw: dict) -> CdmPublicRecord | None:
    try:
        sat1_id = int(raw.get("SAT_1_ID") or raw.get("SAT1_ID") or 0)
        sat2_id = int(raw.get("SAT_2_ID") or raw.get("SAT2_ID") or 0)
    except (TypeError, ValueError):
        return None
    if sat1_id == 0 or sat2_id == 0:
        return None

    pc_raw = raw.get("PC")
    pc = float(pc_raw) if pc_raw not in (None, "") else None
    min_rng_raw = raw.get("MIN_RNG")
    min_range = float(min_rng_raw) if min_rng_raw not in (None, "") else None
    emergency = raw.get("EMERGENCY_REPORTABLE")
    emergency_bool = None
    if emergency is not None:
        emergency_bool = str(emergency).upper() == "Y"

    return CdmPublicRecord(
        cdm_id=str(raw.get("CDM_ID", "")),
        tca=_parse_tca(raw.get("TCA")),
        pc=pc,
        min_range_km=min_range,
        sat1_id=sat1_id,
        sat2_id=sat2_id,
        sat1_name=raw.get("SAT_1_NAME") or raw.get("SAT1_NAME"),
        sat2_name=raw.get("SAT_2_NAME") or raw.get("SAT2_NAME"),
        emergency_reportable=emergency_bool,
    )


def _records_from_json(payload: list[dict]) -> list[CdmPublicRecord]:
    records: list[CdmPublicRecord] = []
    for item in payload:
        rec = _parse_record(item)
        if rec is not None:
            records.append(rec)
    return records


def _build_query_path(
    norad_id: int | None,
    pc_min: float | None,
    tca_after: datetime | None,
    limit: int,
) -> str:
    parts = ["/basicspacedata/query/class/cdm_public"]
    if norad_id is not None:
        parts.extend(["SAT_1_ID", str(norad_id)])
    if pc_min is not None:
        parts.extend(["PC", f">{pc_min:g}"])
    if tca_after is not None:
        tca_str = tca_after.strftime("%Y-%m-%dT%H:%M:%S")
        parts.extend(["TCA", f">{tca_str}"])
    parts.extend(["orderby", "TCA asc"])
    parts.extend(["limit", str(max(1, min(limit, 100)))])
    parts.extend(["format", "json"])
    return "/".join(parts)


def fetch_cdm_public(
    norad_id: int | None = None,
    pc_min: float | None = None,
    tca_after: datetime | None = None,
    limit: int = 25,
    force_refresh: bool = False,
) -> CdmFetchResult:
    if not spacetrack_client.has_spacetrack_credentials():
        raise RuntimeError("Space-Track credentials not configured")

    _ensure_cache_dir()
    cache_file, cache_meta = _cache_paths(norad_id)

    if not force_refresh and cache_file.exists() and not _is_cache_stale(cache_meta):
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        records = _records_from_json(payload)
        if pc_min is not None:
            records = [r for r in records if r.pc is not None and r.pc >= pc_min]
        if tca_after is not None:
            records = [r for r in records if r.tca is not None and r.tca >= tca_after]
        records = records[:limit]
        return CdmFetchResult(records=records, cached=True, degraded=False)

    path = _build_query_path(norad_id, pc_min, tca_after, limit)
    try:
        payload = spacetrack_client.get_json(path)
    except Exception as exc:
        if cache_file.exists():
            cached_payload = json.loads(cache_file.read_text(encoding="utf-8"))
            records = _records_from_json(cached_payload)[:limit]
            return CdmFetchResult(records=records, cached=True, degraded=True)
        raise RuntimeError(f"Space-Track CDM 取得に失敗しました: {exc}") from exc

    cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    cache_meta.write_text(str(time.time()), encoding="utf-8")
    records = _records_from_json(payload)[:limit]
    return CdmFetchResult(records=records, cached=False, degraded=False)


def default_tca_after(days_ahead: int | None) -> datetime | None:
    if days_ahead is None:
        return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


def tca_before(days_ahead: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days_ahead)
