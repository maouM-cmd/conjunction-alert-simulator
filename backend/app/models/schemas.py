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
    pc: float
    pc_foster: float | None = None
    pc_alfriend: float | None = None
    pc_monte_carlo: float | None = None
    pc_method_used: Literal["foster", "encounter_advanced"] | None = None
    covariance_source: Literal["isotropic", "tle_rtn_anisotropic", "cdm_encounter"] | None = None
    sigma_source: Literal["manual", "cdm_covariance", "tle_age"] | None = None


class WebhookNotifyOut(BaseModel):
    sent: bool
    alert_count: int
    degraded: bool
    message: str


class ConjunctionsRequest(BaseModel):
    tle: str
    duration_days: float = Field(default=7.0, gt=0, le=30)
    threshold_km: float = Field(default=5.0, gt=0)
    step_minutes: int = Field(default=1, ge=1, le=60)
    sigma_km: float | None = Field(default=None, gt=0, description="位置不確かさ上書き (km)")
    use_advanced_pc: bool = Field(default=False, description="encounter plane Alfriend Pc を使用")
    use_anisotropic_cov: bool = Field(
        default=False,
        description="TLE RTN 非等方共分散（use_advanced_pc=true 時のみ有効）",
    )
    notify_webhook: bool = Field(default=False, description="高リスクイベントを Webhook に通知")
    cdm_text: str | None = Field(default=None, description="共分散付き CDM KVN（任意）")
    apply_cdm_covariance: bool = Field(
        default=False,
        description="cdm_text 指定時、該当デブリの Pc に CDM encounter 共分散を適用",
    )
    use_altitude_prefilter: bool = Field(
        default=True,
        description="高度帯±200kmプリフィルタ（500件超カタログ時）",
    )


class ConjunctionsResponse(BaseModel):
    satellite: SatelliteInfo
    analysis_window: AnalysisWindow
    threshold_km: float
    conjunctions: list[ConjunctionOut]
    debris_catalog_count: int
    debris_candidates_count: int
    altitude_prefilter_applied: bool
    computation_time_ms: int
    tle_cache_stale: bool
    tle_provider: str
    webhook: WebhookNotifyOut | None = None


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
    tle_provider: str
    spacetrack_configured: bool
    spacetrack_cdm_available: bool = False
    alert_delivery_configured: bool = False
    alert_delivery_format: str | None = None


class CdmParseRequest(BaseModel):
    cdm_text: str = Field(min_length=1)


class CdmRecordOut(BaseModel):
    tca: datetime | None
    miss_distance_km: float | None
    relative_speed_kms: float | None
    pc_external: float | None
    sat1_designator: str | None
    sat2_designator: str | None
    sat1_object: str | None
    sat2_object: str | None


class CdmCompareRequest(BaseModel):
    cdm_text: str = Field(min_length=1)
    satellite_tle: str
    debris_tle: str
    duration_days: float = Field(default=7.0, gt=0, le=30)
    step_minutes: int = Field(default=1, ge=1, le=60)
    sigma_km: float | None = Field(default=None, gt=0)


class CdmCompareSide(BaseModel):
    miss_distance_km: float | None
    pc: float | None
    relative_velocity_kms: float | None = None
    tca: datetime | None = None


class PcMethodsOut(BaseModel):
    foster: float | None
    alfriend: float | None
    monte_carlo: float | None


class CdmCompareResponse(BaseModel):
    cdm: CdmCompareSide
    cas: CdmCompareSide
    delta_miss_km: float | None
    delta_pc_ratio: float | None
    cas_sigma_km: float | None
    sigma_source: Literal["manual", "cdm_covariance", "tle_age"]
    pc_methods: PcMethodsOut
    pc_method_used: Literal["foster_only", "encounter_advanced"]
    encounter_miss_km: float | None


class SatelliteInput(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    tle: str


class BatchConjunctionsRequest(BaseModel):
    satellites: list[SatelliteInput] = Field(min_length=1, max_length=25)
    threshold_km: float = Field(default=50.0, gt=0)
    duration_days: float = Field(default=7.0, gt=0, le=30)
    step_minutes: int = Field(default=1, ge=1, le=60)
    sigma_km: float | None = Field(default=None, gt=0)
    use_advanced_pc: bool = Field(default=False, description="encounter plane Alfriend Pc を使用")
    use_anisotropic_cov: bool = Field(
        default=False,
        description="TLE RTN 非等方共分散（use_advanced_pc=true 時のみ有効）",
    )
    notify_webhook: bool = Field(default=False, description="高リスクイベントを Webhook に一括通知")
    use_altitude_prefilter: bool = Field(
        default=True,
        description="高度帯±200kmプリフィルタ（500件超カタログ時）",
    )


class BatchSummaryOut(BaseModel):
    satellite_count: int
    total_events: int
    highest_pc: float
    highest_pc_satellite: str | None
    highest_pc_debris: str | None


class BatchConjunctionsResponse(BaseModel):
    results: list[ConjunctionsResponse]
    summary: BatchSummaryOut
    computation_time_ms: int
    tle_provider: str
    parallel: bool
    worker_count: int
    webhook: WebhookNotifyOut | None = None


class CdmPublicRecordOut(BaseModel):
    cdm_id: str
    tca: datetime | None
    pc: float | None
    min_range_km: float | None
    sat1_id: int
    sat2_id: int
    sat1_name: str | None
    sat2_name: str | None
    emergency_reportable: bool | None
    has_rtn_covariance: bool = False


class CdmFetchRequest(BaseModel):
    norad_id: int = Field(ge=1, description="監視対象衛星 NORAD ID")
    pc_min: float | None = Field(default=None, ge=0, description="Pc 下限フィルタ")
    days_ahead: int | None = Field(default=7, ge=1, le=30, description="TCA 前方日数")
    limit: int = Field(default=25, ge=1, le=100)


class CdmFetchResponse(BaseModel):
    records: list[CdmPublicRecordOut]
    source: Literal["spacetrack"] = "spacetrack"
    cached: bool
    degraded: bool


class CdmCompareAlertRequest(BaseModel):
    satellite_tle: str
    record: CdmPublicRecordOut
    duration_days: float = Field(default=7.0, gt=0, le=30)
    step_minutes: int = Field(default=1, ge=1, le=60)
    sigma_km: float | None = Field(default=None, gt=0)


class CdmCompareAlertResponse(BaseModel):
    compare: CdmCompareResponse
    debris_tle: str
    debris_norad_id: int


class CdmExportRequest(BaseModel):
    satellite_tle: str
    debris_tle: str
    tca: datetime
    miss_distance_km: float
    relative_velocity_kms: float
    pc: float
    sigma_km: float | None = Field(default=None, gt=0)


class CdmExportResponse(BaseModel):
    cdm_text: str
