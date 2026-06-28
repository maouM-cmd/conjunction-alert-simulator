"""Map ConjunctionEvent to API output."""

from __future__ import annotations

from backend.app.models.schemas import ConjunctionOut
from backend.app.services.conjunction import ConjunctionEvent


def event_to_conjunction_out(event: ConjunctionEvent) -> ConjunctionOut:
    method = event.pc_method_used
    return ConjunctionOut(
        debris_norad_id=event.debris_norad_id,
        debris_name=event.debris_name,
        debris_tle=event.debris_tle,
        tca=event.tca,
        miss_distance_km=round(event.miss_distance_km, 4),
        relative_velocity_kms=round(event.relative_velocity_kms, 4),
        risk_level=event.risk_level,  # type: ignore[arg-type]
        pc=event.pc,
        pc_foster=event.pc_foster,
        pc_alfriend=event.pc_alfriend,
        pc_monte_carlo=event.pc_monte_carlo,
        pc_method_used=method,  # type: ignore[arg-type]
        covariance_source=event.covariance_source,  # type: ignore[arg-type]
        sigma_source=event.sigma_source,  # type: ignore[arg-type]
    )
