"""Backward-compatible re-exports (Phase 10I)."""

from backend.app.auth.principal import (  # noqa: F401
    AuthPrincipal,
    authorize_key_management,
    check_fleet_access,
    get_auth_principal,
    is_admin_key,
    principal_scoped_fleet_id,
    require_admin_principal,
)
