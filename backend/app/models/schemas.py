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
    auto_spacetrack_cdm: bool = Field(
        default=False,
        description="Space-Track cdm_public から CDM を取得し該当デブリに共分散を適用",
    )
    spacetrack_cdm_pc_min: float | None = Field(
        default=None,
        ge=0,
        description="auto_spacetrack_cdm 時の Pc 下限フィルタ",
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
    spacetrack_cdm_records_fetched: int = 0
    spacetrack_cdm_events_merged: int = 0
    spacetrack_cdm_degraded: bool = False


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
    status: Literal["ok", "degraded"] = "ok"
    checks: dict[str, Literal["ok", "error", "skipped"]] = Field(default_factory=dict)
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
    auto_spacetrack_cdm: bool = Field(
        default=False,
        description="Space-Track cdm_public から CDM を自動取得し該当デブリに共分散を適用",
    )
    spacetrack_cdm_pc_min: float | None = Field(
        default=None,
        ge=0,
        description="auto_spacetrack_cdm 時の Pc 下限フィルタ",
    )


class BatchSummaryOut(BaseModel):
    satellite_count: int
    total_events: int
    highest_pc: float
    highest_pc_satellite: str | None
    highest_pc_debris: str | None
    spacetrack_cdm_events_merged: int = 0
    spacetrack_cdm_satellites_with_merge: int = 0


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


class FleetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class FleetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    tags: list[str] | None = None


class FleetOut(BaseModel):
    id: str
    name: str
    description: str | None
    tags: list[str]
    active: bool
    created_at: datetime
    updated_at: datetime
    satellite_count: int | None = None


class SatelliteCreate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    norad_id: int | None = None
    tle: str = Field(min_length=1)


class SatelliteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    tle: str | None = Field(default=None, min_length=1)


class SatelliteOut(BaseModel):
    id: str
    fleet_id: str
    name: str
    norad_id: int
    tle: str
    tle_updated_at: datetime
    active: bool


class SatelliteListOut(BaseModel):
    items: list[SatelliteOut]
    total: int
    limit: int
    offset: int


class TleRevisionOut(BaseModel):
    id: str
    satellite_id: str
    tle: str
    created_at: datetime


ScreeningRunStatus = Literal["pending", "running", "completed", "failed", "dead_letter"]


class ScreeningScheduleCreate(BaseModel):
    fleet_id: str
    name: str = Field(min_length=1, max_length=255)
    cron_expression: str = Field(min_length=9, max_length=128)
    threshold_km: float = Field(default=5.0, gt=0)
    duration_days: float = Field(default=7.0, gt=0, le=30)
    step_minutes: int = Field(default=1, ge=1, le=60)
    use_advanced_pc: bool = False
    use_altitude_prefilter: bool = True
    auto_spacetrack_cdm: bool = False
    spacetrack_cdm_pc_min: float | None = Field(default=None, ge=0)
    notify_on_complete: bool = False


class ScreeningScheduleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    cron_expression: str | None = Field(default=None, min_length=9, max_length=128)
    threshold_km: float | None = Field(default=None, gt=0)
    duration_days: float | None = Field(default=None, gt=0, le=30)
    step_minutes: int | None = Field(default=None, ge=1, le=60)
    use_advanced_pc: bool | None = None
    use_altitude_prefilter: bool | None = None
    auto_spacetrack_cdm: bool | None = None
    spacetrack_cdm_pc_min: float | None = Field(default=None, ge=0)
    notify_on_complete: bool | None = None


class ScreeningScheduleOut(BaseModel):
    id: str
    fleet_id: str
    name: str
    cron_expression: str
    threshold_km: float
    duration_days: float
    step_minutes: int
    use_advanced_pc: bool
    use_altitude_prefilter: bool
    auto_spacetrack_cdm: bool
    spacetrack_cdm_pc_min: float | None
    notify_on_complete: bool
    active: bool
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ScreeningRunOut(BaseModel):
    id: str
    schedule_id: str | None
    fleet_id: str
    status: ScreeningRunStatus
    started_at: datetime | None
    finished_at: datetime | None
    satellite_count: int
    event_count: int
    degraded: bool
    retry_count: int
    error_message: str | None
    computation_time_ms: int | None
    created_at: datetime


class ScreeningRunListOut(BaseModel):
    items: list[ScreeningRunOut]
    total: int
    limit: int
    offset: int


AlertStatus = Literal[
    "open", "acknowledged", "mitigation_planned", "closed", "false_positive"
]


ManeuverDirection = Literal["prograde", "retrograde", "normal"]


class MitigationPreviewRequest(BaseModel):
    direction: ManeuverDirection = "prograde"
    delta_v_ms: float = 0.01
    duration_days: float = 7.0
    step_minutes: int = 1


class MitigationPreviewOut(BaseModel):
    id: str
    alert_id: str
    direction: str
    delta_v_ms: float
    before_tca: datetime
    before_miss_distance_km: float
    after_tca: datetime
    after_miss_distance_km: float
    relative_velocity_kms: float | None
    trigger_source: str
    api_key_id: str | None
    created_at: datetime


class MitigationPreviewListOut(BaseModel):
    items: list[MitigationPreviewOut]
    total: int


class MitigationSweepRequest(BaseModel):
    direction: ManeuverDirection = "prograde"
    delta_v_min_ms: float = 0.01
    delta_v_max_ms: float = 0.10
    delta_v_step_ms: float = 0.01
    max_trials: int = Field(default=20, ge=1, le=50)
    duration_days: float = 7.0
    step_minutes: int = 1


class MitigationSweepOut(BaseModel):
    items: list[MitigationPreviewOut]
    best: MitigationPreviewOut | None
    total: int


class MitigationPlanRequest(BaseModel):
    preview_id: str | None = None
    comment: str | None = None


class PcRefinementOut(BaseModel):
    id: str
    alert_id: str
    pc_screening: float
    pc_refined: float
    pc_method: str
    covariance_source: str | None
    miss_distance_km: float
    trigger_source: str
    api_key_id: str | None
    created_at: datetime


class PcRefinementListOut(BaseModel):
    items: list[PcRefinementOut]
    total: int


class ConjunctionAlertOut(BaseModel):
    id: str
    fleet_id: str
    satellite_id: str
    satellite_name: str
    satellite_norad_id: int
    screening_run_id: str | None
    debris_norad_id: int
    debris_name: str
    tca: datetime
    pc: float
    miss_distance_km: float
    risk_level: str
    status: AlertStatus
    comment: str | None
    created_at: datetime
    updated_at: datetime
    latest_mitigation_preview: MitigationPreviewOut | None = None
    latest_pc_refinement: PcRefinementOut | None = None
    escalated: bool = False
    auto_mitigation_planned: bool = False


class ConjunctionAlertListOut(BaseModel):
    items: list[ConjunctionAlertOut]
    total: int
    limit: int
    offset: int


class AlertTransition(BaseModel):
    status: AlertStatus
    comment: str | None = None


class FleetOpsSummaryOut(BaseModel):
    fleet_id: str
    fleet_name: str
    open_count: int
    acknowledged_count: int
    mitigation_planned_count: int
    closed_count: int
    false_positive_count: int
    latest_run_id: str | None
    latest_run_status: str | None
    latest_run_finished_at: datetime | None


class FleetSlaOut(BaseModel):
    fleet_id: str
    fleet_name: str
    has_active_schedule: bool
    last_completed_run_at: datetime | None
    screening_lag_seconds: float | None
    screening_lag_hours: float | None
    screening_sla_ok: bool
    screening_sla_target_hours: float


class SlaSummaryOut(BaseModel):
    items: list[FleetSlaOut]
    overdue_count: int
    screening_sla_target_hours: float


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ApiKeyCreatedOut(BaseModel):
    id: str
    fleet_id: str
    name: str
    key_prefix: str
    api_key: str
    created_at: datetime


class ApiKeyOut(BaseModel):
    id: str
    fleet_id: str
    name: str
    key_prefix: str
    created_at: datetime


class AuditLogOut(BaseModel):
    id: str
    fleet_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    api_key_id: str | None
    detail: dict
    created_at: datetime


class AuditLogListOut(BaseModel):
    items: list[AuditLogOut]
    total: int
    limit: int
    offset: int
