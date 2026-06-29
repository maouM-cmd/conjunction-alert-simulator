"""Authentication principals: API Key + OIDC session (Phase 9E / 10I)."""

from __future__ import annotations

import secrets
import uuid
from typing import NamedTuple

from fastapi import Cookie, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.db.models import ApiKey
from backend.app.db.session import require_db
from backend.app.services import api_key_service, oidc_config, oidc_service
from backend.app.services.auth_config import get_admin_api_key, is_api_key_required


class AuthPrincipal(NamedTuple):
    api_key: ApiKey | None
    is_admin: bool
    oidc_email: str | None = None
    oidc_fleet_id: uuid.UUID | None = None


def is_admin_key(header_key: str | None) -> bool:
    admin = get_admin_api_key()
    if not admin or not header_key:
        return False
    return secrets.compare_digest(header_key, admin)


def _principal_from_session(
  cas_ops_session: str | None,
) -> AuthPrincipal | None:
    claims = oidc_service.verify_session_token(cas_ops_session)
    if claims is None:
        return None
    return AuthPrincipal(
        None,
        claims.is_admin,
        oidc_email=claims.email,
        oidc_fleet_id=claims.fleet_id,
    )


def _finalize_principal(request: Request, principal: AuthPrincipal) -> AuthPrincipal:
    request.state.fleet_id_for_api_slo = principal_scoped_fleet_id(principal)
    return principal


def get_auth_principal(
    request: Request,
    db: Session = Depends(require_db),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    cas_ops_session: str | None = Cookie(default=None, alias="cas_ops_session"),
) -> AuthPrincipal:
    if not is_api_key_required():
        session_principal = _principal_from_session(cas_ops_session)
        if session_principal is not None:
            return _finalize_principal(request, session_principal)
        return _finalize_principal(request, AuthPrincipal(None, False))
    if is_admin_key(x_api_key):
        return _finalize_principal(request, AuthPrincipal(None, True))
    if x_api_key:
        record = api_key_service.verify_api_key(db, x_api_key)
        if record is None:
            raise HTTPException(status_code=401, detail="無効な API Key です。")
        return _finalize_principal(request, AuthPrincipal(record, False))
    session_principal = _principal_from_session(cas_ops_session)
    if session_principal is not None:
        return _finalize_principal(request, session_principal)
    raise HTTPException(status_code=401, detail="API Key が必要です。")


def require_admin_principal(
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> AuthPrincipal:
    if not is_api_key_required():
        return principal
    if not principal.is_admin:
        raise HTTPException(status_code=403, detail="管理者 API Key が必要です。")
    return principal


def principal_scoped_fleet_id(principal: AuthPrincipal) -> uuid.UUID | None:
    if principal.is_admin:
        return None
    if principal.api_key is not None:
        return principal.api_key.fleet_id
    return principal.oidc_fleet_id


def check_fleet_access(principal: AuthPrincipal, fleet_id: uuid.UUID) -> None:
    if not is_api_key_required():
        return
    if principal.is_admin:
        return
    if principal.api_key is not None and principal.api_key.fleet_id == fleet_id:
        return
    if principal.oidc_fleet_id == fleet_id:
        return
    if principal.api_key is None and principal.oidc_email is None:
        raise HTTPException(status_code=401, detail="API Key が必要です。")
    raise HTTPException(status_code=403, detail="この艦隊へのアクセス権がありません。")


def authorize_key_management(
    db: Session,
    fleet_id: uuid.UUID,
    principal: AuthPrincipal,
) -> None:
    if not is_api_key_required():
        return
    if principal.is_admin:
        return
    active_count = api_key_service.count_active_keys(db, fleet_id)
    if active_count == 0:
        raise HTTPException(status_code=403, detail="初回 API Key は管理者キーで作成してください。")
    check_fleet_access(principal, fleet_id)
