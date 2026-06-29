"""Per-fleet conjunction alert Prometheus metrics (Phase 10Q)."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import ConjunctionAlert, Fleet

ALERT_STATUSES = (
    "open",
    "acknowledged",
    "mitigation_planned",
    "closed",
    "false_positive",
)


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


def list_active_fleets(db: Session) -> list[Fleet]:
    return list(
        db.execute(select(Fleet).where(Fleet.active.is_(True)).order_by(Fleet.name)).scalars().all()
    )


def collect_fleet_alert_counts(db: Session) -> dict[uuid.UUID, dict[str, int]]:
    """Return per-fleet alert counts for all active fleets (missing statuses default to 0)."""
    result: dict[uuid.UUID, dict[str, int]] = {
        fleet.id: {status: 0 for status in ALERT_STATUSES} for fleet in list_active_fleets(db)
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


def render_fleet_alert_rules(fleet_id: uuid.UUID, fleet_name: str) -> list[dict[str, Any]]:
    threshold = fleet_open_alert_threshold()
    fid = str(fleet_id)
    return [
        {
            "alert": "CASFleetOpenAlertsHigh",
            "expr": f'cas_fleet_alerts_total{{fleet_id="{fid}",status="open"}} > {threshold}',
            "for": "5m",
            "labels": {"fleet_id": fid},
            "annotations": {
                "summary": f"Fleet {fleet_name} has too many open alerts",
            },
        }
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
