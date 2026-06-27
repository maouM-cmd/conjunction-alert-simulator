"""Health check endpoint."""

from fastapi import APIRouter

from backend.app.models.schemas import HealthResponse
from backend.app.services.tle_fetcher import cache_age_hours, is_cache_stale

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        tle_cache_age_hours=cache_age_hours(),
        tle_cache_stale=is_cache_stale(),
    )
