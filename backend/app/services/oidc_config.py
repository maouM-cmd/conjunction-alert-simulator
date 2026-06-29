"""OIDC / session configuration (Phase 10I)."""

from __future__ import annotations

import json
import os
import uuid


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "true" if default else "false").strip().lower()
    return raw in ("1", "true", "yes")


def oidc_enabled() -> bool:
    if not _env_bool("OPS_OIDC_ENABLED", default=False):
        return False
    return bool(session_secret() and oidc_issuer() and oidc_client_id() and oidc_redirect_uri())


def oidc_issuer() -> str | None:
    raw = os.getenv("OPS_OIDC_ISSUER", "").strip()
    return raw.rstrip("/") if raw else None


def oidc_client_id() -> str | None:
    raw = os.getenv("OPS_OIDC_CLIENT_ID", "").strip()
    return raw or None


def oidc_client_secret() -> str | None:
    raw = os.getenv("OPS_OIDC_CLIENT_SECRET", "").strip()
    return raw or None


def oidc_redirect_uri() -> str | None:
    raw = os.getenv("OPS_OIDC_REDIRECT_URI", "").strip()
    return raw or None


def session_secret() -> str | None:
    raw = os.getenv("OPS_SESSION_SECRET", "").strip()
    return raw or None


def session_ttl_hours() -> float:
    raw = os.getenv("OPS_SESSION_TTL_HOURS", "8").strip()
    try:
        return max(float(raw), 0.25)
    except ValueError:
        return 8.0


def session_cookie_name() -> str:
    return "cas_ops_session"


def parse_admin_emails() -> set[str]:
    raw = os.getenv("OPS_OIDC_ADMIN_EMAILS", "").strip()
    if not raw:
        return set()
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def parse_fleet_mappings() -> dict[uuid.UUID, set[str]]:
    raw = os.getenv("OPS_OIDC_FLEET_MAPPINGS", "{}").strip() or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    mappings: dict[uuid.UUID, set[str]] = {}
    for fleet_id, emails in data.items():
        try:
            fid = uuid.UUID(str(fleet_id))
        except ValueError:
            continue
        if isinstance(emails, str):
            email_list = [emails]
        elif isinstance(emails, list):
            email_list = emails
        else:
            continue
        normalized = {str(e).strip().lower() for e in email_list if str(e).strip()}
        if normalized:
            mappings[fid] = normalized
    return mappings
