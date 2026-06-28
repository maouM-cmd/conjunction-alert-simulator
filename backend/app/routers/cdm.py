"""CDM parse, compare, fetch, and export API."""

from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import (
    CdmCompareAlertRequest,
    CdmCompareAlertResponse,
    CdmCompareRequest,
    CdmCompareResponse,
    CdmCompareSide,
    CdmExportRequest,
    CdmExportResponse,
    CdmFetchRequest,
    CdmFetchResponse,
    CdmParseRequest,
    CdmPublicRecordOut,
    CdmRecordOut,
    PcMethodsOut,
)
from backend.app.services import spacetrack_client
from backend.app.services.cdm_alert_compare import compare_cdm_alert
from backend.app.services.cdm_compare import CdmCompareResult, compare_cdm_with_tles
from backend.app.services.cdm_export import export_from_tle_and_conjunction
from backend.app.services.cdm_parser import parse_cdm
from backend.app.services.spacetrack_cdm_fetcher import (
    CdmPublicRecord,
    default_tca_after,
    fetch_cdm_public,
    tca_before,
)

router = APIRouter(prefix="/api/v1/cdm", tags=["cdm"])

COMPUTATION_TIMEOUT_SEC = 90.0


def _record_to_out(record: CdmPublicRecord) -> CdmPublicRecordOut:
    return CdmPublicRecordOut(
        cdm_id=record.cdm_id,
        tca=record.tca,
        pc=record.pc,
        min_range_km=record.min_range_km,
        sat1_id=record.sat1_id,
        sat2_id=record.sat2_id,
        sat1_name=record.sat1_name,
        sat2_name=record.sat2_name,
        emergency_reportable=record.emergency_reportable,
        has_rtn_covariance=record.has_rtn_covariance(),
    )


def _record_from_out(out: CdmPublicRecordOut) -> CdmPublicRecord:
    return CdmPublicRecord(
        cdm_id=out.cdm_id,
        tca=out.tca,
        pc=out.pc,
        min_range_km=out.min_range_km,
        sat1_id=out.sat1_id,
        sat2_id=out.sat2_id,
        sat1_name=out.sat1_name,
        sat2_name=out.sat2_name,
        emergency_reportable=out.emergency_reportable,
    )


def _compare_to_response(result: CdmCompareResult) -> CdmCompareResponse:
    cdm = result.cdm
    cas_tca = None
    if result.cas_tca:
        cas_tca = datetime.fromisoformat(result.cas_tca.replace("Z", "+00:00"))

    return CdmCompareResponse(
        cdm=CdmCompareSide(
            miss_distance_km=cdm.miss_distance_km,
            pc=cdm.pc_external,
            relative_velocity_kms=cdm.relative_speed_kms,
            tca=cdm.tca,
        ),
        cas=CdmCompareSide(
            miss_distance_km=round(result.cas_miss_distance_km, 4),
            pc=result.cas_pc,
            relative_velocity_kms=round(result.cas_relative_velocity_kms, 4),
            tca=cas_tca,
        ),
        delta_miss_km=round(result.delta_miss_km, 4) if result.delta_miss_km is not None else None,
        delta_pc_ratio=round(result.delta_pc_ratio, 4) if result.delta_pc_ratio is not None else None,
        cas_sigma_km=round(result.cas_sigma_km, 4),
        sigma_source=result.sigma_source,
        pc_methods=PcMethodsOut(
            foster=result.pc_methods.foster,
            alfriend=result.pc_methods.alfriend,
            monte_carlo=result.pc_methods.monte_carlo,
        ),
        pc_method_used=result.pc_method_used,
        encounter_miss_km=(
            round(result.encounter_miss_km, 4) if result.encounter_miss_km is not None else None
        ),
    )


@router.post("/parse", response_model=CdmRecordOut)
async def parse_cdm_api(body: CdmParseRequest) -> CdmRecordOut:
    try:
        record = await asyncio.to_thread(parse_cdm, body.cdm_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CdmRecordOut(
        tca=record.tca,
        miss_distance_km=record.miss_distance_km,
        relative_speed_kms=record.relative_speed_kms,
        pc_external=record.pc_external,
        sat1_designator=record.sat1_designator,
        sat2_designator=record.sat2_designator,
        sat1_object=record.sat1_object,
        sat2_object=record.sat2_object,
    )


@router.post("/compare", response_model=CdmCompareResponse)
async def compare_cdm_api(body: CdmCompareRequest) -> CdmCompareResponse:
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                compare_cdm_with_tles,
                body.cdm_text,
                body.satellite_tle,
                body.debris_tle,
                body.duration_days,
                body.step_minutes,
                body.sigma_km,
            ),
            timeout=COMPUTATION_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="CDM 比較がタイムアウトしました（90秒超）。",
        ) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _compare_to_response(result)


@router.post("/fetch", response_model=CdmFetchResponse)
async def fetch_cdm_api(body: CdmFetchRequest) -> CdmFetchResponse:
    if not spacetrack_client.has_spacetrack_credentials():
        raise HTTPException(
            status_code=503,
            detail="Space-Track 認証が未設定です。.env に SPACE_TRACK_USER / PASSWORD を設定してください。",
        )

    tca_after = default_tca_after(body.days_ahead)
    tca_limit = tca_before(body.days_ahead) if body.days_ahead else None

    try:
        result = await asyncio.to_thread(
            fetch_cdm_public,
            body.norad_id,
            body.pc_min,
            tca_after,
            body.limit,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    records = result.records
    if tca_limit is not None:
        records = [r for r in records if r.tca is not None and r.tca <= tca_limit]

    return CdmFetchResponse(
        records=[_record_to_out(r) for r in records],
        cached=result.cached,
        degraded=result.degraded,
    )


@router.post("/compare-alert", response_model=CdmCompareAlertResponse)
async def compare_alert_api(body: CdmCompareAlertRequest) -> CdmCompareAlertResponse:
    record = _record_from_out(body.record)
    try:
        result, debris_tle = await asyncio.wait_for(
            asyncio.to_thread(
                compare_cdm_alert,
                body.satellite_tle,
                record,
                body.duration_days,
                body.step_minutes,
                body.sigma_km,
            ),
            timeout=COMPUTATION_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="CDM アラート比較がタイムアウトしました（90秒超）。",
        ) from None
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    from backend.app.services.tle_parser import parse_tle

    debris_norad = parse_tle(debris_tle).norad_id
    return CdmCompareAlertResponse(
        compare=_compare_to_response(result),
        debris_tle=debris_tle,
        debris_norad_id=debris_norad,
    )


@router.post("/export", response_model=CdmExportResponse)
async def export_cdm_api(body: CdmExportRequest) -> CdmExportResponse:
    try:
        cdm_text = await asyncio.to_thread(
            export_from_tle_and_conjunction,
            body.satellite_tle,
            body.debris_tle,
            tca=body.tca,
            miss_distance_km=body.miss_distance_km,
            relative_velocity_kms=body.relative_velocity_kms,
            pc=body.pc,
            sigma_km=body.sigma_km,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CdmExportResponse(cdm_text=cdm_text)
