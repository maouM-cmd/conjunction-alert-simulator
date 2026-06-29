"""Health check endpoint."""

from fastapi import APIRouter

from backend.app.models.schemas import HealthResponse
from backend.app.services import spacetrack_fetcher
from backend.app.services.health_checks import aggregate_status, run_health_checks
from backend.app.services.tle_fetcher import cache_age_hours, get_active_provider_label, is_cache_stale
from backend.app.services.webhook_notifier import (
    get_alert_delivery_format,
    is_alert_delivery_configured,
)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    checks = run_health_checks()
    return HealthResponse(
        status=aggregate_status(checks),
        checks=checks,
        tle_cache_age_hours=cache_age_hours(),
        tle_cache_stale=is_cache_stale(),
        tle_provider=get_active_provider_label(),
        spacetrack_configured=spacetrack_fetcher.has_spacetrack_credentials(),
        spacetrack_cdm_available=spacetrack_fetcher.has_spacetrack_credentials(),
        alert_delivery_configured=is_alert_delivery_configured(),
        alert_delivery_format=get_alert_delivery_format(),
    )
