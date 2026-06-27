"""CDM parse and compare API."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import (
    CdmCompareRequest,
    CdmCompareResponse,
    CdmCompareSide,
    CdmParseRequest,
    CdmRecordOut,
)
from backend.app.services.cdm_compare import compare_cdm_with_tles
from backend.app.services.cdm_parser import parse_cdm

router = APIRouter(prefix="/api/v1/cdm", tags=["cdm"])

COMPUTATION_TIMEOUT_SEC = 90.0


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

    cdm = result.cdm
    cas_tca = None
    if result.cas_tca:
        from datetime import datetime

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
    )
