"""FastAPI dependencies for API Key auth (Phase 9E)."""

from __future__ import annotations

import secrets
import uuid
from typing import NamedTuple

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.models import ApiKey
from backend.app.db.session import require_db
from backend.app.services import api_key_service
from backend.app.services.auth_config import get_admin_api_key, is_api_key_required


class AuthPrincipal(NamedTuple):
    api_key: ApiKey | None
    is_admin: bool


def is_admin_key(header_key: str | None) -> bool:
    admin = get_admin_api_key()
    if not admin or not header_key:
        return False
    return secrets.compare_digest(header_key, admin)


def get_auth_principal(
    db: Session = Depends(require_db),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> AuthPrincipal:
    if not is_api_key_required():
        return AuthPrincipal(None, False)
    if is_admin_key(x_api_key):
        return AuthPrincipal(None, True)
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API Key が必要です。")
    record = api_key_service.verify_api_key(db, x_api_key)
    if record is None:
        raise HTTPException(status_code=401, detail="無効な API Key です。")
    return AuthPrincipal(record, False)


def require_admin_principal(
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> AuthPrincipal:
    if not is_api_key_required():
        return principal
    if not principal.is_admin:
        raise HTTPException(status_code=403, detail="管理者 API Key が必要です。")
    return principal


def check_fleet_access(principal: AuthPrincipal, fleet_id: uuid.UUID) -> None:
    if not is_api_key_required():
        return
    if principal.is_admin:
        return
    if principal.api_key is None:
        raise HTTPException(status_code=401, detail="API Key が必要です。")
    if principal.api_key.fleet_id != fleet_id:
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
