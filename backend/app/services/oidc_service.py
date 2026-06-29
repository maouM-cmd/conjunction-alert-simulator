"""OIDC login flow and signed session tokens (Phase 10I)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any

from authlib.integrations.httpx_client import OAuth2Client

from backend.app.services import oidc_config

_STATE_TTL_SECONDS = 600
_pending_states: dict[str, tuple[str, float]] = {}
_state_lock = threading.Lock()


@dataclass(frozen=True)
class OidcPrincipal:
    email: str
    is_admin: bool
    fleet_id: uuid.UUID | None


@dataclass(frozen=True)
class SessionClaims:
    email: str
    is_admin: bool
    fleet_id: uuid.UUID | None
    exp: float


def _prune_states() -> None:
    now = time.time()
    expired = [key for key, (_, exp) in _pending_states.items() if exp <= now]
    for key in expired:
        _pending_states.pop(key, None)


def create_login_state() -> tuple[str, str]:
    state = secrets.token_urlsafe(24)
    code_verifier = secrets.token_urlsafe(48)
    with _state_lock:
        _prune_states()
        _pending_states[state] = (code_verifier, time.time() + _STATE_TTL_SECONDS)
    return state, code_verifier


def pop_code_verifier(state: str) -> str | None:
    with _state_lock:
        _prune_states()
        entry = _pending_states.pop(state, None)
    if entry is None:
        return None
    verifier, expires_at = entry
    if expires_at <= time.time():
        return None
    return verifier


def reset_oidc_state_for_tests() -> None:
    with _state_lock:
        _pending_states.clear()


def build_authorize_url(state: str, code_verifier: str) -> str:
    issuer = oidc_config.oidc_issuer()
    client_id = oidc_config.oidc_client_id()
    redirect_uri = oidc_config.oidc_redirect_uri()
    if not issuer or not client_id or not redirect_uri:
        raise RuntimeError("OIDC が正しく設定されていません。")

    client = OAuth2Client(
        client_id=client_id,
        client_secret=oidc_config.oidc_client_secret(),
        redirect_uri=redirect_uri,
    )
    uri, _ = client.create_authorization_url(
        f"{issuer}/authorize",
        state=state,
        code_challenge_method="S256",
        code_challenge=_pkce_challenge(code_verifier),
        scope="openid email profile",
    )
    return uri


def exchange_code_for_email(code: str, state: str) -> str:
    code_verifier = pop_code_verifier(state)
    if code_verifier is None:
        raise ValueError("無効または期限切れの OIDC state です。")

    issuer = oidc_config.oidc_issuer()
    client_id = oidc_config.oidc_client_id()
    redirect_uri = oidc_config.oidc_redirect_uri()
    if not issuer or not client_id or not redirect_uri:
        raise RuntimeError("OIDC が正しく設定されていません。")

    metadata_url = f"{issuer}/.well-known/openid-configuration"
    client = OAuth2Client(
        client_id=client_id,
        client_secret=oidc_config.oidc_client_secret(),
        redirect_uri=redirect_uri,
    )
    client.fetch_server_metadata(metadata_url)
    token = client.fetch_token(
        client.token_endpoint,
        code=code,
        code_verifier=code_verifier,
    )
    claims = client.parse_id_token(token, nonce=None)
    email = _extract_email(claims)
    if not email:
        raise ValueError("OIDC id_token に email が含まれていません。")
    return email


def _extract_email(claims: dict[str, Any]) -> str | None:
    for key in ("email", "preferred_username", "upn"):
        value = claims.get(key)
        if isinstance(value, str) and "@" in value:
            return value.strip().lower()
    return None


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def resolve_principal(email: str) -> OidcPrincipal | None:
    normalized = email.strip().lower()
    if normalized in oidc_config.parse_admin_emails():
        return OidcPrincipal(email=normalized, is_admin=True, fleet_id=None)

    for fleet_id, emails in oidc_config.parse_fleet_mappings().items():
        if normalized in emails:
            return OidcPrincipal(email=normalized, is_admin=False, fleet_id=fleet_id)
    return None


def create_session_token(
    email: str,
    *,
    is_admin: bool,
    fleet_id: uuid.UUID | None,
) -> str:
    secret = oidc_config.session_secret()
    if not secret:
        raise RuntimeError("OPS_SESSION_SECRET が設定されていません。")
    ttl_seconds = oidc_config.session_ttl_hours() * 3600.0
    payload = {
        "email": email.strip().lower(),
        "is_admin": is_admin,
        "fleet_id": str(fleet_id) if fleet_id else None,
        "exp": time.time() + ttl_seconds,
    }
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify_session_token(token: str | None) -> SessionClaims | None:
    if not token:
        return None
    secret = oidc_config.session_secret()
    if not secret or "." not in token:
        return None
    body, sig = token.rsplit(".", 1)
    expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(body.encode()).decode())
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    exp = payload.get("exp")
    email = payload.get("email")
    if not isinstance(exp, (int, float)) or exp <= time.time():
        return None
    if not isinstance(email, str) or not email:
        return None
    fleet_raw = payload.get("fleet_id")
    fleet_id: uuid.UUID | None = None
    if isinstance(fleet_raw, str) and fleet_raw:
        try:
            fleet_id = uuid.UUID(fleet_raw)
        except ValueError:
            return None
    is_admin = bool(payload.get("is_admin"))
    if is_admin:
        fleet_id = None
    return SessionClaims(
        email=email.lower(),
        is_admin=is_admin,
        fleet_id=fleet_id,
        exp=float(exp),
    )
