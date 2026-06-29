"""Tests for OIDC SSO (Phase 10I)."""

from __future__ import annotations

import json
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.auth.principal import get_auth_principal
from backend.app.db.models import AuditLog, Base
from backend.app.db.session import get_engine, get_session_factory, reset_engine_for_tests
from backend.app.services import fleet_service, oidc_service
from backend.app.services.oidc_service import OidcPrincipal


@pytest.fixture(autouse=True)
def reset_oidc_state():
    oidc_service.reset_oidc_state_for_tests()
    yield
    oidc_service.reset_oidc_state_for_tests()


@pytest.fixture
def hardened_client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.delenv("CAS_API_KEY_REQUIRED", raising=False)
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    from backend.app.main import app

    with TestClient(app) as client:
        yield client
    reset_engine_for_tests()


def _enable_oidc(
    monkeypatch,
    *,
    admin_emails: str = "",
    fleet_mappings: dict | None = None,
    session_secret: str = "test-session-secret",
) -> None:
    monkeypatch.setenv("OPS_OIDC_ENABLED", "true")
    monkeypatch.setenv("OPS_SESSION_SECRET", session_secret)
    monkeypatch.setenv("OPS_OIDC_ISSUER", "https://idp.example.com")
    monkeypatch.setenv("OPS_OIDC_CLIENT_ID", "cas-client")
    monkeypatch.setenv("OPS_OIDC_CLIENT_SECRET", "cas-secret")
    monkeypatch.setenv(
        "OPS_OIDC_REDIRECT_URI",
        "http://testserver/api/v1/auth/oidc/callback",
    )
    monkeypatch.setenv("OPS_OIDC_ADMIN_EMAILS", admin_emails)
    monkeypatch.setenv(
        "OPS_OIDC_FLEET_MAPPINGS",
        json.dumps(fleet_mappings or {}),
    )


def _session_cookie(
    email: str,
    *,
    is_admin: bool = False,
    fleet_id: uuid.UUID | None = None,
) -> dict[str, str]:
    token = oidc_service.create_session_token(
        email,
        is_admin=is_admin,
        fleet_id=fleet_id,
    )
    return {"cas_ops_session": token}


def test_oidc_config_disabled(hardened_client):
    response = hardened_client.get("/api/v1/auth/oidc/config")
    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_oidc_config_enabled(hardened_client, monkeypatch):
    _enable_oidc(monkeypatch, admin_emails="admin@example.com")
    response = hardened_client.get("/api/v1/auth/oidc/config")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["login_path"] == "/api/v1/auth/oidc/login"


def test_resolve_principal_admin_and_fleet(monkeypatch):
    fleet_id = uuid.uuid4()
    _enable_oidc(
        monkeypatch,
        admin_emails="admin@example.com",
        fleet_mappings={str(fleet_id): ["ops@example.com"]},
    )
    admin = oidc_service.resolve_principal("admin@example.com")
    assert admin == OidcPrincipal(email="admin@example.com", is_admin=True, fleet_id=None)
    fleet = oidc_service.resolve_principal("ops@example.com")
    assert fleet == OidcPrincipal(
        email="ops@example.com", is_admin=False, fleet_id=fleet_id
    )
    assert oidc_service.resolve_principal("unknown@example.com") is None


def test_session_cookie_admin_access(hardened_client, monkeypatch):
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    _enable_oidc(monkeypatch, admin_emails="admin@example.com")
    fleet_a = hardened_client.post(
        "/api/v1/fleets",
        json={"name": "Fleet A"},
        cookies=_session_cookie("admin@example.com", is_admin=True),
    )
    assert fleet_a.status_code == 201
    fleet_b = hardened_client.post(
        "/api/v1/fleets",
        json={"name": "Fleet B"},
        cookies=_session_cookie("admin@example.com", is_admin=True),
    )
    assert fleet_b.status_code == 201


def test_session_cookie_fleet_scoped_ops(hardened_client, monkeypatch):
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    _enable_oidc(monkeypatch, admin_emails="admin@example.com")
    admin_cookie = _session_cookie("admin@example.com", is_admin=True)
    fleet_a = hardened_client.post(
        "/api/v1/fleets",
        json={"name": "Fleet A"},
        cookies=admin_cookie,
    ).json()
    fleet_b = hardened_client.post(
        "/api/v1/fleets",
        json={"name": "Fleet B"},
        cookies=admin_cookie,
    ).json()
    _enable_oidc(
        monkeypatch,
        admin_emails="admin@example.com",
        fleet_mappings={fleet_a["id"]: ["ops@example.com"]},
    )
    fleet_cookie = _session_cookie(
        "ops@example.com",
        fleet_id=uuid.UUID(fleet_a["id"]),
    )
    own = hardened_client.get(
        f"/api/v1/ops/alerts?fleet_id={fleet_a['id']}",
        cookies=fleet_cookie,
    )
    assert own.status_code == 200
    other = hardened_client.get(
        f"/api/v1/ops/alerts?fleet_id={fleet_b['id']}",
        cookies=fleet_cookie,
    )
    assert other.status_code == 403


def test_fleet_oidc_lists_single_fleet(hardened_client, monkeypatch, db_session):
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    db = db_session
    fleet = fleet_service.create_fleet(db, name="OIDC Fleet")
    fleet_service.create_fleet(db, name="Other Fleet")
    _enable_oidc(
        monkeypatch,
        fleet_mappings={str(fleet.id): ["ops@example.com"]},
    )
    listing = hardened_client.get(
        "/api/v1/fleets",
        cookies=_session_cookie("ops@example.com", fleet_id=fleet.id),
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["id"] == str(fleet.id)


@pytest.fixture
def db_session(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    reset_engine_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()
        reset_engine_for_tests()


@patch("backend.app.routers.auth.oidc_service.exchange_code_for_email")
def test_oidc_callback_sets_cookie_and_audit(
    mock_exchange, hardened_client, monkeypatch, db_session
):
    monkeypatch.setenv("CAS_API_KEY_REQUIRED", "true")
    fleet = fleet_service.create_fleet(db_session, name="Callback Fleet")
    _enable_oidc(
        monkeypatch,
        fleet_mappings={str(fleet.id): ["ops@example.com"]},
    )
    mock_exchange.return_value = "ops@example.com"
    state, _ = oidc_service.create_login_state()

    response = hardened_client.get(
        "/api/v1/auth/oidc/callback",
        params={"code": "dummy-code", "state": state},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == "/app/?tab=ops"
    assert "cas_ops_session" in response.cookies

    db = get_session_factory()()
    try:
        audit = (
            db.query(AuditLog)
            .filter(AuditLog.action == "auth.oidc_login")
            .one()
        )
        assert audit.detail["email"] == "ops@example.com"
    finally:
        db.close()

    me = hardened_client.get("/api/v1/auth/me", cookies=response.cookies)
    assert me.status_code == 200
    assert me.json()["authenticated"] is True
    assert me.json()["fleet_id"] == str(fleet.id)


def test_logout_clears_session(hardened_client, monkeypatch):
    _enable_oidc(monkeypatch, admin_emails="admin@example.com")
    hardened_client.cookies.update(_session_cookie("admin@example.com", is_admin=True))
    assert hardened_client.get("/api/v1/auth/me").json()["authenticated"]
    logout = hardened_client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
    assert "cas_ops_session=" in logout.headers.get("set-cookie", "")
    hardened_client.cookies.pop("cas_ops_session", None)
    me = hardened_client.get("/api/v1/auth/me")
    assert me.json()["authenticated"] is False


def test_unknown_email_callback_forbidden(hardened_client, monkeypatch):
    _enable_oidc(monkeypatch, admin_emails="admin@example.com")
    state, _ = oidc_service.create_login_state()
    with patch(
        "backend.app.routers.auth.oidc_service.exchange_code_for_email",
        return_value="unknown@example.com",
    ):
        response = hardened_client.get(
            "/api/v1/auth/oidc/callback",
            params={"code": "dummy", "state": state},
        )
    assert response.status_code == 403
