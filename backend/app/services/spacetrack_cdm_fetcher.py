"""Space-Track cdm_public fetcher with file cache."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.app.services import spacetrack_client
from backend.app.services.cdm_covariance import parse_variance_km2_from_spacetrack, rtn_has_data
from backend.app.services.cdm_types import RtnVariance

CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "cache"
TTL_SECONDS = 24 * 3600

_RTN_SUFFIXES = ("CR_R", "CT_T", "CN_N", "CR_T", "CR_N", "CT_N")


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
    relative_speed_kms: float | None = None
    sat1_rtn: RtnVariance | None = None
    sat2_rtn: RtnVariance | None = None

    def has_rtn_covariance(self) -> bool:
        return rtn_has_data(self.sat1_rtn) or rtn_has_data(self.sat2_rtn)


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


def _detail_cache_paths(cdm_id: str) -> tuple[Path, Path]:
    safe_id = re.sub(r"[^\w.-]", "_", cdm_id)
    return (
        CACHE_DIR / f"spacetrack_cdm_detail_{safe_id}.json",
        CACHE_DIR / f"spacetrack_cdm_detail_{safe_id}.meta",
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


def _parse_speed_kms(raw: dict) -> float | None:
    speed_raw = raw.get("RELATIVE_SPEED") or raw.get("RELATIVE_SPEED_KMS")
    if speed_raw in (None, ""):
        return None
    try:
        speed = float(speed_raw)
    except (TypeError, ValueError):
        return None
    unit = str(raw.get("RELATIVE_SPEED_UNIT") or raw.get("RELATIVE_SPEED_KMS_UNIT") or "km/s").lower()
    if unit in ("m/s", "m**1/s"):
        return speed / 1000.0
    return speed


def _parse_min_range_km(raw: dict) -> float | None:
    min_rng_raw = raw.get("MIN_RNG") or raw.get("MISS_DISTANCE")
    if min_rng_raw in (None, ""):
        return None
    try:
        value = float(min_rng_raw)
    except (TypeError, ValueError):
        return None
    unit = str(raw.get("MIN_RNG_UNIT") or raw.get("MISS_DISTANCE_UNIT") or "km").lower()
    if unit in ("m",):
        return value / 1000.0
    return value


def _rtn_from_spacetrack_raw(raw: dict, prefix: str) -> RtnVariance | None:
    values: dict[str, float | None] = {}
    for suffix in _RTN_SUFFIXES:
        key = f"{prefix}_{suffix}"
        val = raw.get(key)
        if val in (None, ""):
            values[suffix.lower()] = None
            continue
        unit = raw.get(f"{key}_UNIT")
        try:
            values[suffix.lower()] = parse_variance_km2_from_spacetrack(val, str(unit) if unit else None)
        except ValueError:
            values[suffix.lower()] = None

    rtn = RtnVariance(
        cr_r=values.get("cr_r"),
        ct_t=values.get("ct_t"),
        cn_n=values.get("cn_n"),
        cr_t=values.get("cr_t"),
        cr_n=values.get("cr_n"),
        ct_n=values.get("ct_n"),
    )
    return rtn if rtn_has_data(rtn) else None


def _parse_record(raw: dict) -> CdmPublicRecord | None:
    try:
        sat1_id = int(raw.get("SAT_1_ID") or raw.get("SAT1_ID") or raw.get("SAT1_OBJECT_DESIGNATOR") or 0)
        sat2_id = int(raw.get("SAT_2_ID") or raw.get("SAT2_ID") or raw.get("SAT2_OBJECT_DESIGNATOR") or 0)
    except (TypeError, ValueError):
        return None
    if sat1_id == 0 or sat2_id == 0:
        return None

    pc_raw = raw.get("PC") or raw.get("COLLISION_PROBABILITY")
    pc = float(pc_raw) if pc_raw not in (None, "") else None
    emergency = raw.get("EMERGENCY_REPORTABLE")
    emergency_bool = None
    if emergency is not None:
        emergency_bool = str(emergency).upper() == "Y"

    return CdmPublicRecord(
        cdm_id=str(raw.get("CDM_ID", "")),
        tca=_parse_tca(raw.get("TCA")),
        pc=pc,
        min_range_km=_parse_min_range_km(raw),
        sat1_id=sat1_id,
        sat2_id=sat2_id,
        sat1_name=raw.get("SAT_1_NAME") or raw.get("SAT1_NAME") or raw.get("SAT1_OBJECT"),
        sat2_name=raw.get("SAT_2_NAME") or raw.get("SAT2_NAME") or raw.get("SAT2_OBJECT"),
        emergency_reportable=emergency_bool,
        relative_speed_kms=_parse_speed_kms(raw),
        sat1_rtn=_rtn_from_spacetrack_raw(raw, "SAT1"),
        sat2_rtn=_rtn_from_spacetrack_raw(raw, "SAT2"),
    )


def merge_cdm_records(base: CdmPublicRecord, detail: CdmPublicRecord) -> CdmPublicRecord:
    """Merge list summary with detail fetch (RTN fields from detail)."""
    return replace(
        base,
        tca=detail.tca or base.tca,
        pc=detail.pc if detail.pc is not None else base.pc,
        min_range_km=detail.min_range_km if detail.min_range_km is not None else base.min_range_km,
        sat1_name=detail.sat1_name or base.sat1_name,
        sat2_name=detail.sat2_name or base.sat2_name,
        relative_speed_kms=detail.relative_speed_kms or base.relative_speed_kms,
        sat1_rtn=detail.sat1_rtn or base.sat1_rtn,
        sat2_rtn=detail.sat2_rtn or base.sat2_rtn,
    )


def _records_from_json(payload: list[dict]) -> list[CdmPublicRecord]:
    records: list[CdmPublicRecord] = []
    for item in payload:
        rec = _parse_record(item)
        if rec is not None:
            records.append(rec)
    return records


def _payload_to_record(payload: list[dict] | dict) -> CdmPublicRecord | None:
    if isinstance(payload, list):
        if not payload:
            return None
        return _parse_record(payload[0])
    if isinstance(payload, dict):
        return _parse_record(payload)
    return None


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


def _build_detail_path(cdm_id: str) -> str:
    return f"/basicspacedata/query/class/cdm_public/CDM_ID/{cdm_id}/format/json"


def fetch_cdm_detail(cdm_id: str, force_refresh: bool = False) -> CdmPublicRecord | None:
    """Fetch single CDM by ID (may include RTN covariance fields)."""
    if not cdm_id:
        return None
    if not spacetrack_client.has_spacetrack_credentials():
        raise RuntimeError("Space-Track credentials not configured")

    _ensure_cache_dir()
    cache_file, cache_meta = _detail_cache_paths(cdm_id)

    if not force_refresh and cache_file.exists() and not _is_cache_stale(cache_meta):
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        return _payload_to_record(payload)

    path = _build_detail_path(cdm_id)
    try:
        payload = spacetrack_client.get_json(path)
    except Exception as exc:
        if cache_file.exists():
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
            return _payload_to_record(payload)
        raise RuntimeError(f"Space-Track CDM 詳細取得に失敗しました: {exc}") from exc

    cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    cache_meta.write_text(str(time.time()), encoding="utf-8")
    return _payload_to_record(payload)


def enrich_record_with_rtn(record: CdmPublicRecord) -> CdmPublicRecord:
    """Lazy-fetch CDM detail when list record lacks RTN covariance."""
    if record.has_rtn_covariance() or not record.cdm_id:
        return record
    try:
        detail = fetch_cdm_detail(record.cdm_id)
    except RuntimeError:
        return record
    if detail is None:
        return record
    return merge_cdm_records(record, detail)


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
