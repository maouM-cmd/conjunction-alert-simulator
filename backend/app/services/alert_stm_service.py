"""Alert state transition matrix — single source of truth (Phase 10R / 10T)."""

from __future__ import annotations

import os
from typing import Any

ALL_ALERT_STATUSES: tuple[str, ...] = (
    "open",
    "escalated",
    "acknowledged",
    "mitigation_planned",
    "closed",
    "false_positive",
)

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "open": {"acknowledged", "false_positive", "escalated"},
    "escalated": {"acknowledged", "false_positive"},
    "acknowledged": {"mitigation_planned", "false_positive", "closed"},
    "mitigation_planned": {"closed", "false_positive"},
    "closed": set(),
    "false_positive": set(),
}

REOPEN_TO_OPEN_SOURCES: frozenset[str] = frozenset(
    {"acknowledged", "escalated", "false_positive"}
)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def stm_auto_escalate_status_enabled() -> bool:
    return _env_bool("ALERT_STM_AUTO_ESCALATE_STATUS", default=False)


def reopen_to_open_enabled() -> bool:
    return _env_bool("ALERT_STM_REOPEN_TO_OPEN_ENABLED", default=False)


def effective_allowed_transitions() -> dict[str, set[str]]:
    transitions = {status: set(targets) for status, targets in ALLOWED_TRANSITIONS.items()}
    if reopen_to_open_enabled():
        for from_status in REOPEN_TO_OPEN_SOURCES:
            transitions.setdefault(from_status, set()).add("open")
    return transitions


def is_transition_allowed(from_status: str, to_status: str) -> bool:
    return to_status in effective_allowed_transitions().get(from_status, set())


def allowed_targets(from_status: str) -> list[str]:
    return sorted(effective_allowed_transitions().get(from_status, set()))


def target_for_acknowledge(from_status: str) -> str | None:
    if from_status in ("open", "escalated"):
        return "acknowledged"
    return None


def transition_chain_for_resolve(from_status: str) -> list[str]:
    if from_status in ("closed", "false_positive"):
        return []
    if from_status in ("open", "escalated"):
        return ["acknowledged", "closed"]
    if from_status in ("acknowledged", "mitigation_planned"):
        return ["closed"]
    return []


def stm_matrix() -> list[list[bool]]:
    return [
        [is_transition_allowed(from_status, to_status) for to_status in ALL_ALERT_STATUSES]
        for from_status in ALL_ALERT_STATUSES
    ]


def state_machine_payload() -> dict[str, Any]:
    return {
        "statuses": list(ALL_ALERT_STATUSES),
        "allowed_transitions": {
            status: allowed_targets(status) for status in ALL_ALERT_STATUSES
        },
        "matrix": stm_matrix(),
        "reopen_to_open_enabled": reopen_to_open_enabled(),
    }
