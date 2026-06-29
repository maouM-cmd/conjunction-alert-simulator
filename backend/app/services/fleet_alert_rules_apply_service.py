"""Prometheus fleet alert rules file apply (Phase 10AG)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FleetAlertRulesApplyResult:
    applied: bool
    path: str | None
    message: str


def prometheus_fleet_rules_output_path() -> str | None:
    raw = os.getenv("PROMETHEUS_FLEET_RULES_OUTPUT_PATH", "").strip()
    return raw or None


def apply_fleet_alert_rules(content: str, *, format: str) -> FleetAlertRulesApplyResult:
    path = prometheus_fleet_rules_output_path()
    if path is None:
        return FleetAlertRulesApplyResult(
            applied=False,
            path=None,
            message="PROMETHEUS_FLEET_RULES_OUTPUT_PATH が未設定です。ダウンロードして手動適用してください。",
        )

    target = Path(path)
    parent = target.parent
    if not parent.exists():
        return FleetAlertRulesApplyResult(
            applied=False,
            path=str(target),
            message=f"出力先ディレクトリが存在しません: {parent}",
        )

    suffix = ".json" if format.lower() == "json" else ".yaml"
    if target.suffix != suffix:
        target = target.with_suffix(suffix)
    tmp_path = target.with_name(target.name + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, target)

    return FleetAlertRulesApplyResult(
        applied=True,
        path=str(target),
        message=f"ルールを {target} に書き込みました。",
    )
