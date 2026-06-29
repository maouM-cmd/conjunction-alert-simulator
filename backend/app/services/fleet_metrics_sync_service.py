"""Fleet alert metrics export and breach sync (Phase 10U)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from backend.app.metrics_registry import (
    cas_fleet_alerts_by_risk_total,
    cas_fleet_alerts_total,
    cas_fleet_high_risk_open_breach,
    cas_fleet_open_alerts_breach,
)
from backend.app.services import alertmanager_push_service, fleet_alert_metrics_service


def collect_and_export_fleet_metrics(
    db: Session,
    *,
    sync_breaches: bool = True,
) -> tuple[
    dict[uuid.UUID, dict[str, int]],
    dict[uuid.UUID, dict[str, dict[str, int]]],
    dict[uuid.UUID, str],
]:
    """Collect per-fleet counts, update Prometheus gauges, optionally sync AM breaches."""
    if not fleet_alert_metrics_service.fleet_alert_metrics_enabled():
        return {}, {}, {}

    counts = fleet_alert_metrics_service.collect_fleet_alert_counts(db)
    risk_counts = fleet_alert_metrics_service.collect_fleet_risk_counts(db)
    open_threshold = fleet_alert_metrics_service.fleet_open_alert_threshold()
    high_risk_threshold = fleet_alert_metrics_service.fleet_high_risk_open_threshold()
    fleets = fleet_alert_metrics_service.list_active_fleets(db)
    fleet_names = {fleet.id: fleet.name for fleet in fleets}

    cas_fleet_alerts_total.clear()
    cas_fleet_open_alerts_breach.clear()
    cas_fleet_alerts_by_risk_total.clear()
    cas_fleet_high_risk_open_breach.clear()

    for fleet_id, status_counts in counts.items():
        fleet_id_str = str(fleet_id)
        open_count = status_counts.get("open", 0)
        for status, count in status_counts.items():
            cas_fleet_alerts_total.labels(fleet_id=fleet_id_str, status=status).set(count)
        breach = 1.0 if open_count > open_threshold else 0.0
        cas_fleet_open_alerts_breach.labels(fleet_id=fleet_id_str).set(breach)

    for fleet_id, risk_status in risk_counts.items():
        fleet_id_str = str(fleet_id)
        high_open = risk_status.get("high", {}).get("open", 0)
        for risk_level, status_counts in risk_status.items():
            for status, count in status_counts.items():
                cas_fleet_alerts_by_risk_total.labels(
                    fleet_id=fleet_id_str,
                    risk_level=risk_level,
                    status=status,
                ).set(count)
        high_breach = 1.0 if high_open >= high_risk_threshold else 0.0
        cas_fleet_high_risk_open_breach.labels(fleet_id=fleet_id_str).set(high_breach)

    if sync_breaches:
        alertmanager_push_service.sync_breaches(counts, risk_counts, fleet_names)

    return counts, risk_counts, fleet_names
