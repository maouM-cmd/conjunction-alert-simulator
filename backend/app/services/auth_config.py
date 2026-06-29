"""Production hardening config (Phase 9E)."""

from __future__ import annotations

import os


def is_api_key_required() -> bool:
    return os.getenv("CAS_API_KEY_REQUIRED", "").strip().lower() in ("1", "true", "yes")


def get_admin_api_key() -> str | None:
    raw = os.getenv("CAS_ADMIN_API_KEY", "").strip()
    return raw or None
