"""Per-fleet conjunction alert Prometheus metrics (Phase 10Q / 10S)."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import ConjunctionAlert, Fleet

from backend.app.services.alert_stm_service import ALL_ALERT_STATUSES

ALERT_STATUSES = ALL_ALERT_STATUSES
RISK_LEVELS = ("high", "medium", "low")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def fleet_alert_metrics_enabled() -> bool:
    return _env_bool("FLEET_ALERT_METRICS_ENABLED", default=False)


def fleet_open_alert_threshold() -> int:
    raw = os.environ.get("FLEET_ALERT_OPEN_THRESHOLD", "").strip()
    if not raw:
        return 10
    try:
        return max(int(raw), 1)
    except ValueError:
        return 10


def fleet_high_risk_open_threshold() -> int:
    raw = os.environ.get("FLEET_ALERT_HIGH_RISK_THRESHOLD", "").strip()
    if not raw:
        return 1
    try:
        return max(int(raw), 1)
    except ValueError:
        return 1


def list_active_fleets(db: Session) -> list[Fleet]:
    return list(
        db.execute(select(Fleet).where(Fleet.active.is_(True)).order_by(Fleet.name)).scalars().all()
    )


def _empty_status_counts() -> dict[str, int]:
    return {status: 0 for status in ALERT_STATUSES}


def _empty_risk_status_counts() -> dict[str, dict[str, int]]:
    return {risk: _empty_status_counts() for risk in RISK_LEVELS}


def collect_fleet_alert_counts(db: Session) -> dict[uuid.UUID, dict[str, int]]:
    """Return per-fleet alert counts for all active fleets (missing statuses default to 0)."""
    result: dict[uuid.UUID, dict[str, int]] = {
        fleet.id: _empty_status_counts() for fleet in list_active_fleets(db)
    }
    rows = db.execute(
        select(ConjunctionAlert.fleet_id, ConjunctionAlert.status, func.count())
        .join(Fleet, Fleet.id == ConjunctionAlert.fleet_id)
        .where(Fleet.active.is_(True))
        .group_by(ConjunctionAlert.fleet_id, ConjunctionAlert.status)
    ).all()
    for fleet_id, status, count in rows:
        if fleet_id not in result:
            continue
        if status in result[fleet_id]:
            result[fleet_id][status] = int(count)
    return result


def collect_fleet_risk_counts(db: Session) -> dict[uuid.UUID, dict[str, dict[str, int]]]:
    """Return per-fleet counts by risk_level and status for active fleets."""
    result: dict[uuid.UUID, dict[str, dict[str, int]]] = {
        fleet.id: _empty_risk_status_counts() for fleet in list_active_fleets(db)
    }
    rows = db.execute(
        select(
            ConjunctionAlert.fleet_id,
            ConjunctionAlert.risk_level,
            ConjunctionAlert.status,
            func.count(),
        )
        .join(Fleet, Fleet.id == ConjunctionAlert.fleet_id)
        .where(Fleet.active.is_(True))
        .group_by(
            ConjunctionAlert.fleet_id,
            ConjunctionAlert.risk_level,
            ConjunctionAlert.status,
        )
    ).all()
    for fleet_id, risk_level, status, count in rows:
        if fleet_id not in result:
            continue
        if risk_level in result[fleet_id] and status in result[fleet_id][risk_level]:
            result[fleet_id][risk_level][status] = int(count)
    return result


def collect_open_risk_counts(db: Session, fleet_id: uuid.UUID) -> dict[str, int]:
    """Open alert counts grouped by risk_level for one fleet."""
    counts = {risk: 0 for risk in RISK_LEVELS}
    rows = db.execute(
        select(ConjunctionAlert.risk_level, func.count())
        .where(
            ConjunctionAlert.fleet_id == fleet_id,
            ConjunctionAlert.status == "open",
        )
        .group_by(ConjunctionAlert.risk_level)
    ).all()
    for risk_level, count in rows:
        if risk_level in counts:
            counts[risk_level] = int(count)
    return counts


def render_fleet_alert_rules(fleet_id: uuid.UUID, fleet_name: str) -> list[dict[str, Any]]:
    open_threshold = fleet_open_alert_threshold()
    high_risk_threshold = fleet_high_risk_open_threshold()
    fid = str(fleet_id)
    return [
        {
            "alert": "CASFleetOpenAlertsHigh",
            "expr": f'cas_fleet_alerts_total{{fleet_id="{fid}",status="open"}} > {open_threshold}',
            "for": "5m",
            "labels": {"fleet_id": fid},
            "annotations": {
                "summary": f"Fleet {fleet_name} has too many open alerts",
            },
        },
        {
            "alert": "CASFleetHighRiskOpenAlerts",
            "expr": (
                f'cas_fleet_alerts_by_risk_total{{fleet_id="{fid}",risk_level="high",status="open"}}'
                f" >= {high_risk_threshold}"
            ),
            "for": "5m",
            "labels": {"fleet_id": fid, "severity": "critical"},
            "annotations": {
                "summary": f"Fleet {fleet_name} has high-risk open alerts",
            },
        },
    ]


def render_fleet_alert_rules_yaml(rules: list[dict[str, Any]]) -> str:
    lines = ["groups:", "  - name: cas-fleet-alerts", "    rules:"]
    for rule in rules:
        lines.append(f"      - alert: {rule['alert']}")
        lines.append(f'        expr: {rule["expr"]}')
        lines.append(f"        for: {rule['for']}")
        lines.append("        labels:")
        for key, value in rule["labels"].items():
            lines.append(f'          {key}: "{value}"')
        lines.append("        annotations:")
        for key, value in rule["annotations"].items():
            escaped = str(value).replace('"', '\\"')
            lines.append(f'          {key}: "{escaped}"')
    return "\n".join(lines) + "\n"


def render_fleet_alert_rules_json(rules: list[dict[str, Any]]) -> str:
    payload = {"groups": [{"name": "cas-fleet-alerts", "rules": rules}]}
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
