"""Health check endpoint."""

from fastapi import APIRouter

from backend.app.models.schemas import HealthResponse
from backend.app.services import spacetrack_fetcher
from backend.app.services.tle_fetcher import cache_age_hours, get_active_provider_label, is_cache_stale

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        tle_cache_age_hours=cache_age_hours(),
        tle_cache_stale=is_cache_stale(),
        tle_provider=get_active_provider_label(),
        spacetrack_configured=spacetrack_fetcher.has_spacetrack_credentials(),
    )
