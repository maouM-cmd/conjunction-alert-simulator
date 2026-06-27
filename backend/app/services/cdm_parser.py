"""CCSDS CDM/KDM text parser (key fields only)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

_CDM_LINE = re.compile(r"^\s*([A-Z0-9_]+)\s*=\s*(.+?)\s*$")


@dataclass(frozen=True)
class CdmRecord:
    tca: datetime | None
    miss_distance_km: float | None
    relative_speed_kms: float | None
    pc_external: float | None
    sat1_designator: str | None
    sat2_designator: str | None
    sat1_object: str | None
    sat2_object: str | None
    raw_fields: dict[str, str] = field(default_factory=dict)


def _parse_tca(value: str) -> datetime:
    """Parse CCSDS TCA: YYYY/DDD/HH:MM:SS.sss or ISO-like."""
    value = value.strip()
    if "/" in value and value.count("/") >= 2:
        date_part, time_part = value.split("/", 1)
        year = int(date_part)
        rest = time_part.split("/")
        doy = int(rest[0])
        time_str = rest[1] if len(rest) > 1 else "00:00:00.000"
        base = datetime(year, 1, 1, tzinfo=timezone.utc)
        day_dt = base + timedelta(days=doy - 1)
        h, m, s = time_str.split(":")
        sec = float(s)
        return day_dt.replace(hour=int(h), minute=int(m), second=int(sec), microsecond=int((sec % 1) * 1e6))
    if value.endswith("Z"):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def _parse_float_with_unit(value: str) -> float:
    value = value.strip()
    match = re.match(r"^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*(\w*)", value)
    if not match:
        raise ValueError(f"数値を解析できません: {value}")
    number = float(match.group(1))
    unit = match.group(2).lower()
    if unit in ("m", "meter", "meters"):
        return number / 1000.0
    if unit in ("km", "kilometer", "kilometers", ""):
        return number
    if unit in ("m/s", "m/s"):
        return number / 1000.0
    if unit in ("km/s", "km/s"):
        return number
    return number


def _parse_speed_kms(value: str) -> float:
    v = value.strip().lower()
    if "km/s" in v:
        return float(v.replace("km/s", "").strip())
    if "m/s" in v:
        return float(v.replace("m/s", "").strip()) / 1000.0
    return _parse_float_with_unit(value)


def parse_cdm(text: str) -> CdmRecord:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = _CDM_LINE.match(line)
        if match:
            fields[match.group(1)] = match.group(2).strip()

    if not fields:
        raise ValueError("CDM 形式の key=value 行が見つかりません。")

    tca = None
    if "TCA" in fields:
        tca = _parse_tca(fields["TCA"])

    miss_km = None
    if "MISS_DISTANCE" in fields:
        miss_km = _parse_float_with_unit(fields["MISS_DISTANCE"])

    rel_speed = None
    if "RELATIVE_SPEED" in fields or "RELATIVE_VELOCITY" in fields:
        key = "RELATIVE_SPEED" if "RELATIVE_SPEED" in fields else "RELATIVE_VELOCITY"
        rel_speed = _parse_speed_kms(fields[key])

    pc = None
    if "COLLISION_PROBABILITY" in fields:
        pc = float(fields["COLLISION_PROBABILITY"].split()[0])

    return CdmRecord(
        tca=tca,
        miss_distance_km=miss_km,
        relative_speed_kms=rel_speed,
        pc_external=pc,
        sat1_designator=fields.get("SAT1_OBJECT_DESIGNATOR") or fields.get("SAT1_ID"),
        sat2_designator=fields.get("SAT2_OBJECT_DESIGNATOR") or fields.get("SAT2_ID"),
        sat1_object=fields.get("SAT1_OBJECT") or fields.get("SAT1_NAME"),
        sat2_object=fields.get("SAT2_OBJECT") or fields.get("SAT2_NAME"),
        raw_fields=fields,
    )
