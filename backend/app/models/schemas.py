"""Pydantic request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PositionKm(BaseModel):
    x: float
    y: float
    z: float


class OrbitPointOut(BaseModel):
    time: datetime
    position_km: PositionKm


class SatelliteInfo(BaseModel):
    name: str
    norad_id: int


class AnalysisWindow(BaseModel):
    start: datetime
    end: datetime


class ConjunctionOut(BaseModel):
    debris_norad_id: int
    debris_name: str
    debris_tle: str
    tca: datetime
    miss_distance_km: float
    relative_velocity_kms: float
    risk_level: Literal["high", "medium", "low"]


class ConjunctionsRequest(BaseModel):
    tle: str
    duration_days: float = Field(default=7.0, gt=0, le=30)
    threshold_km: float = Field(default=5.0, gt=0)
    step_minutes: int = Field(default=1, ge=1, le=60)


class ConjunctionsResponse(BaseModel):
    satellite: SatelliteInfo
    analysis_window: AnalysisWindow
    threshold_km: float
    conjunctions: list[ConjunctionOut]
    debris_catalog_count: int
    computation_time_ms: int
    tle_cache_stale: bool


class OrbitRequest(BaseModel):
    tle: str
    duration_days: float = Field(default=7.0, gt=0, le=30)
    step_minutes: int = Field(default=5, ge=1, le=60)


class OrbitResponse(BaseModel):
    name: str
    norad_id: int
    points: list[OrbitPointOut]


class ClosestApproachOut(BaseModel):
    tca: datetime
    miss_distance_km: float
    relative_velocity_kms: float


class ManeuverPreviewRequest(BaseModel):
    satellite_tle: str
    debris_tle: str
    direction: Literal["prograde", "retrograde", "normal"]
    delta_v_ms: float = Field(ge=0.01, le=1.0)
    duration_days: float = Field(default=7.0, gt=0, le=30)
    step_minutes: int = Field(default=1, ge=1, le=60)


class ManeuverPreviewResponse(BaseModel):
    before: ClosestApproachOut
    after: ClosestApproachOut
    delta_v_applied_ms: float
    direction: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    tle_cache_age_hours: float | None
    tle_cache_stale: bool
