"""OIDC SSO auth routes (Phase 10I)."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from backend.app.db.session import require_db
from backend.app.models.schemas import AuthMeOut, OidcConfigOut
from backend.app.services import audit_service, oidc_config, oidc_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _session_cookie_kwargs(token: str) -> dict:
    ttl_seconds = int(oidc_config.session_ttl_hours() * 3600)
    return {
        "key": oidc_config.session_cookie_name(),
        "value": token,
        "httponly": True,
        "samesite": "lax",
        "max_age": ttl_seconds,
        "path": "/",
    }


@router.get("/oidc/config", response_model=OidcConfigOut)
def oidc_config_endpoint() -> OidcConfigOut:
    enabled = oidc_config.oidc_enabled()
    return OidcConfigOut(
        enabled=enabled,
        login_path="/api/v1/auth/oidc/login" if enabled else None,
    )


@router.get("/oidc/login")
def oidc_login() -> RedirectResponse:
    if not oidc_config.oidc_enabled():
        raise HTTPException(status_code=404, detail="OIDC は有効化されていません。")
    state, verifier = oidc_service.create_login_state()
    url = oidc_service.build_authorize_url(state, verifier)
    return RedirectResponse(url=url, status_code=302)


@router.get("/oidc/callback")
def oidc_callback(
    db: Session = Depends(require_db),
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    if not oidc_config.oidc_enabled():
        raise HTTPException(status_code=404, detail="OIDC は有効化されていません。")
    if error:
        raise HTTPException(status_code=400, detail=f"OIDC エラー: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="OIDC callback パラメータが不足しています。")

    try:
        email = oidc_service.exchange_code_for_email(code, state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="OIDC token 交換に失敗しました。") from exc

    principal = oidc_service.resolve_principal(email)
    if principal is None:
        raise HTTPException(status_code=403, detail="このアカウントには Ops 権限がありません。")

    token = oidc_service.create_session_token(
        principal.email,
        is_admin=principal.is_admin,
        fleet_id=principal.fleet_id,
    )
    audit_service.log_audit(
        db,
        fleet_id=principal.fleet_id,
        action="auth.oidc_login",
        resource_type="auth",
        resource_id=None,
        api_key_id=None,
        detail={
            "email": principal.email,
            "is_admin": principal.is_admin,
            "fleet_id": str(principal.fleet_id) if principal.fleet_id else None,
        },
    )
    db.commit()

    response = RedirectResponse(url="/app/?tab=ops", status_code=302)
    response.set_cookie(**_session_cookie_kwargs(token))
    return response


@router.post("/logout")
def logout() -> Response:
    response = Response(status_code=204)
    response.set_cookie(
        key=oidc_config.session_cookie_name(),
        value="",
        max_age=0,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/me", response_model=AuthMeOut)
def auth_me(
    cas_ops_session: str | None = Cookie(default=None),
) -> AuthMeOut:
    claims = oidc_service.verify_session_token(cas_ops_session)
    if claims is None:
        return AuthMeOut(authenticated=False)
    return AuthMeOut(
        authenticated=True,
        email=claims.email,
        is_admin=claims.is_admin,
        fleet_id=str(claims.fleet_id) if claims.fleet_id else None,
    )
