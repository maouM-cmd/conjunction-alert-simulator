"""Fleet registry REST API (Phase 9A)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.db.models import Fleet, Satellite
from backend.app.db.session import require_db
from backend.app.models.schemas import (
    FleetCreate,
    FleetOut,
    FleetUpdate,
    SatelliteCreate,
    SatelliteListOut,
    SatelliteOut,
    SatelliteUpdate,
)
from backend.app.services import fleet_service

router = APIRouter(prefix="/api/v1", tags=["fleets"])


def _fleet_out(fleet: Fleet, *, satellite_count: int | None = None) -> FleetOut:
    return FleetOut(
        id=str(fleet.id),
        name=fleet.name,
        description=fleet.description,
        tags=fleet.tags or [],
        active=fleet.active,
        created_at=fleet.created_at,
        updated_at=fleet.updated_at,
        satellite_count=satellite_count,
    )


def _satellite_out(satellite: Satellite) -> SatelliteOut:
    return SatelliteOut(
        id=str(satellite.id),
        fleet_id=str(satellite.fleet_id),
        name=satellite.name,
        norad_id=satellite.norad_id,
        tle=satellite.tle,
        tle_updated_at=satellite.tle_updated_at,
        active=satellite.active,
    )


def _parse_uuid(value: str, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"無効な {label} です。") from exc


def _handle_service_error(exc: fleet_service.FleetServiceError) -> HTTPException:
    if isinstance(exc, fleet_service.NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, fleet_service.ConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, fleet_service.ValidationError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.post("/fleets", response_model=FleetOut, status_code=201)
def create_fleet(body: FleetCreate, db: Session = Depends(require_db)) -> FleetOut:
    fleet = fleet_service.create_fleet(
        db, name=body.name, description=body.description, tags=body.tags
    )
    return _fleet_out(fleet, satellite_count=0)


@router.get("/fleets", response_model=list[FleetOut])
def list_fleets(db: Session = Depends(require_db)) -> list[FleetOut]:
    fleets = fleet_service.list_fleets(db)
    return [
        _fleet_out(f, satellite_count=fleet_service.count_active_satellites(db, f.id))
        for f in fleets
    ]


@router.get("/fleets/{fleet_id}", response_model=FleetOut)
def get_fleet(fleet_id: str, db: Session = Depends(require_db)) -> FleetOut:
    fid = _parse_uuid(fleet_id, "fleet_id")
    try:
        fleet = fleet_service.get_fleet(db, fid)
    except fleet_service.FleetServiceError as exc:
        raise _handle_service_error(exc) from exc
    return _fleet_out(fleet, satellite_count=fleet_service.count_active_satellites(db, fid))


@router.patch("/fleets/{fleet_id}", response_model=FleetOut)
def update_fleet(
    fleet_id: str, body: FleetUpdate, db: Session = Depends(require_db)
) -> FleetOut:
    fid = _parse_uuid(fleet_id, "fleet_id")
    try:
        fleet = fleet_service.update_fleet(
            db, fid, name=body.name, description=body.description, tags=body.tags
        )
    except fleet_service.FleetServiceError as exc:
        raise _handle_service_error(exc) from exc
    return _fleet_out(fleet, satellite_count=fleet_service.count_active_satellites(db, fid))


@router.delete("/fleets/{fleet_id}", status_code=204)
def delete_fleet(fleet_id: str, db: Session = Depends(require_db)) -> None:
    fid = _parse_uuid(fleet_id, "fleet_id")
    try:
        fleet_service.delete_fleet(db, fid)
    except fleet_service.FleetServiceError as exc:
        raise _handle_service_error(exc) from exc


@router.post("/fleets/{fleet_id}/satellites", response_model=SatelliteOut, status_code=201)
def add_satellite(
    fleet_id: str, body: SatelliteCreate, db: Session = Depends(require_db)
) -> SatelliteOut:
    fid = _parse_uuid(fleet_id, "fleet_id")
    try:
        satellite = fleet_service.add_satellite(
            db, fid, name=body.name, norad_id=body.norad_id, tle=body.tle
        )
    except fleet_service.FleetServiceError as exc:
        raise _handle_service_error(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _satellite_out(satellite)


@router.get("/fleets/{fleet_id}/satellites", response_model=SatelliteListOut)
def list_satellites(
    fleet_id: str,
    db: Session = Depends(require_db),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> SatelliteListOut:
    fid = _parse_uuid(fleet_id, "fleet_id")
    try:
        items, total = fleet_service.list_satellites(db, fid, limit=limit, offset=offset)
    except fleet_service.FleetServiceError as exc:
        raise _handle_service_error(exc) from exc
    return SatelliteListOut(
        items=[_satellite_out(s) for s in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/satellites/{satellite_id}", response_model=SatelliteOut)
def update_satellite(
    satellite_id: str, body: SatelliteUpdate, db: Session = Depends(require_db)
) -> SatelliteOut:
    sid = _parse_uuid(satellite_id, "satellite_id")
    if body.name is None and body.tle is None:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください。")
    try:
        satellite = fleet_service.update_satellite(db, sid, name=body.name, tle=body.tle)
    except fleet_service.FleetServiceError as exc:
        raise _handle_service_error(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _satellite_out(satellite)


@router.delete("/satellites/{satellite_id}", status_code=204)
def delete_satellite(satellite_id: str, db: Session = Depends(require_db)) -> None:
    sid = _parse_uuid(satellite_id, "satellite_id")
    try:
        fleet_service.delete_satellite(db, sid)
    except fleet_service.FleetServiceError as exc:
        raise _handle_service_error(exc) from exc


@router.post("/satellites/{satellite_id}/rollback", response_model=SatelliteOut)
def rollback_satellite_tle(
    satellite_id: str, db: Session = Depends(require_db)
) -> SatelliteOut:
    sid = _parse_uuid(satellite_id, "satellite_id")
    try:
        satellite = fleet_service.rollback_satellite_tle(db, sid)
    except fleet_service.FleetServiceError as exc:
        raise _handle_service_error(exc) from exc
    return _satellite_out(satellite)
