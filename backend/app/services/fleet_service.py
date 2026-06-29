"""Fleet registry CRUD and TLE revision management."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db.models import Fleet, Satellite, TleRevision
from backend.app.services.scale_config import fleet_max_satellites
from backend.app.services.tle_parser import parse_tle

MAX_TLE_REVISIONS = 2


class FleetServiceError(Exception):
    """Base error for fleet service."""


class NotFoundError(FleetServiceError):
    pass


class ConflictError(FleetServiceError):
    pass


class ValidationError(FleetServiceError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_tle(tle: str) -> str:
    parsed = parse_tle(tle)
    return parsed.text


def _touch_fleet(db: Session, fleet: Fleet) -> None:
    fleet.updated_at = _utcnow()


def _trim_revisions(db: Session, satellite_id: uuid.UUID) -> None:
    revisions = (
        db.execute(
            select(TleRevision)
            .where(TleRevision.satellite_id == satellite_id)
            .order_by(TleRevision.created_at.desc())
        )
        .scalars()
        .all()
    )
    for old in revisions[MAX_TLE_REVISIONS:]:
        db.delete(old)


def create_fleet(
    db: Session,
    *,
    name: str,
    description: str | None = None,
    tags: list[str] | None = None,
) -> Fleet:
    fleet = Fleet(name=name, description=description, tags=tags or [])
    db.add(fleet)
    db.commit()
    db.refresh(fleet)
    return fleet


def list_fleets(db: Session) -> list[Fleet]:
    return list(
        db.execute(select(Fleet).where(Fleet.active.is_(True)).order_by(Fleet.created_at.desc())).scalars().all()
    )


def get_fleet(db: Session, fleet_id: uuid.UUID) -> Fleet:
    fleet = db.get(Fleet, fleet_id)
    if fleet is None or not fleet.active:
        raise NotFoundError("艦隊が見つかりません。")
    return fleet


def count_active_satellites(db: Session, fleet_id: uuid.UUID) -> int:
    return int(
        db.execute(
            select(func.count())
            .select_from(Satellite)
            .where(Satellite.fleet_id == fleet_id, Satellite.active.is_(True))
        ).scalar_one()
    )


def update_fleet(
    db: Session,
    fleet_id: uuid.UUID,
    *,
    name: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
) -> Fleet:
    fleet = get_fleet(db, fleet_id)
    if name is not None:
        fleet.name = name
    if description is not None:
        fleet.description = description
    if tags is not None:
        fleet.tags = tags
    _touch_fleet(db, fleet)
    db.commit()
    db.refresh(fleet)
    return fleet


def delete_fleet(db: Session, fleet_id: uuid.UUID) -> None:
    fleet = get_fleet(db, fleet_id)
    fleet.active = False
    _touch_fleet(db, fleet)
    db.commit()


def add_satellite(
    db: Session,
    fleet_id: uuid.UUID,
    *,
    name: str | None,
    norad_id: int | None,
    tle: str,
) -> Satellite:
    fleet = get_fleet(db, fleet_id)
    active_count = count_active_satellites(db, fleet_id)
    if active_count >= fleet_max_satellites():
        raise ConflictError(
            f"艦隊の衛星数は最大 {fleet_max_satellites()} 件です。"
        )
    normalized = _normalize_tle(tle)
    parsed = parse_tle(normalized)
    sat_name = name or parsed.name
    sat_norad = norad_id if norad_id is not None else parsed.norad_id
    satellite = Satellite(
        fleet_id=fleet.id,
        name=sat_name,
        norad_id=sat_norad,
        tle=normalized,
        tle_updated_at=_utcnow(),
    )
    db.add(satellite)
    try:
        _touch_fleet(db, fleet)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("同一艦隊内に同じ NORAD ID の衛星が既に存在します。") from exc
    db.refresh(satellite)
    return satellite


def list_all_active_satellites(
    db: Session,
    fleet_id: uuid.UUID,
    *,
    max_count: int | None = None,
) -> list[Satellite]:
    """List all active satellites up to max_count (paginated internally)."""
    get_fleet(db, fleet_id)
    cap = max_count if max_count is not None else fleet_max_satellites()
    items: list[Satellite] = []
    offset = 0
    page_size = 500
    while len(items) < cap:
        batch, total = list_satellites(db, fleet_id, limit=page_size, offset=offset)
        if not batch:
            break
        items.extend(batch)
        offset += len(batch)
        if offset >= total:
            break
    return items[:cap]


def list_satellites(
    db: Session,
    fleet_id: uuid.UUID,
    *,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Satellite], int]:
    get_fleet(db, fleet_id)
    filters = (Satellite.fleet_id == fleet_id, Satellite.active.is_(True))
    total = int(db.execute(select(func.count()).select_from(Satellite).where(*filters)).scalar_one())
    items = list(
        db.execute(
            select(Satellite).where(*filters).order_by(Satellite.norad_id).limit(limit).offset(offset)
        )
        .scalars()
        .all()
    )
    return items, total


def get_satellite(db: Session, satellite_id: uuid.UUID) -> Satellite:
    satellite = db.get(Satellite, satellite_id)
    if satellite is None or not satellite.active:
        raise NotFoundError("衛星が見つかりません。")
    return satellite


def update_satellite(
    db: Session,
    satellite_id: uuid.UUID,
    *,
    name: str | None = None,
    tle: str | None = None,
) -> Satellite:
    satellite = get_satellite(db, satellite_id)
    fleet = get_fleet(db, satellite.fleet_id)
    if name is not None:
        satellite.name = name
    if tle is not None:
        normalized = _normalize_tle(tle)
        if normalized != satellite.tle:
            db.add(
                TleRevision(
                    satellite_id=satellite.id,
                    tle=satellite.tle,
                    created_at=_utcnow(),
                )
            )
            satellite.tle = normalized
            satellite.tle_updated_at = _utcnow()
            db.flush()
            _trim_revisions(db, satellite.id)
    _touch_fleet(db, fleet)
    db.commit()
    db.refresh(satellite)
    return satellite


def delete_satellite(db: Session, satellite_id: uuid.UUID) -> None:
    satellite = get_satellite(db, satellite_id)
    fleet = get_fleet(db, satellite.fleet_id)
    satellite.active = False
    _touch_fleet(db, fleet)
    db.commit()


def rollback_satellite_tle(db: Session, satellite_id: uuid.UUID) -> Satellite:
    satellite = get_satellite(db, satellite_id)
    fleet = get_fleet(db, satellite.fleet_id)
    revision = (
        db.execute(
            select(TleRevision)
            .where(TleRevision.satellite_id == satellite.id)
            .order_by(TleRevision.created_at.desc())
        )
        .scalars()
        .first()
    )
    if revision is None:
        raise NotFoundError("ロールバック可能な TLE 履歴がありません。")
    satellite.tle = revision.tle
    satellite.tle_updated_at = _utcnow()
    db.delete(revision)
    _touch_fleet(db, fleet)
    db.commit()
    db.refresh(satellite)
    return satellite


def list_tle_revisions(db: Session, satellite_id: uuid.UUID) -> list[TleRevision]:
    get_satellite(db, satellite_id)
    return list(
        db.execute(
            select(TleRevision)
            .where(TleRevision.satellite_id == satellite_id)
            .order_by(TleRevision.created_at.desc())
        )
        .scalars()
        .all()
    )
