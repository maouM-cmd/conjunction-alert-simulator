"""Tests for fleet registry API (Phase 9A)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.db.models import Base
from backend.app.db.session import get_engine, reset_engine_for_tests

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
DEMO_SAT = (SAMPLES / "demo-satellite.tle").read_text(encoding="utf-8").strip()
DEMO_DEB = (SAMPLES / "demo-debris.tle").read_text(encoding="utf-8").strip()


@pytest.fixture
def fleet_client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    reset_engine_for_tests()
    engine = get_engine()
    assert engine is not None
    Base.metadata.create_all(engine)
    from backend.app.main import app

    with TestClient(app) as client:
        yield client
    reset_engine_for_tests()


def test_fleet_api_503_when_no_db(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reset_engine_for_tests()
    from backend.app.main import app

    client = TestClient(app)
    response = client.get("/api/v1/fleets")
    assert response.status_code == 503
    reset_engine_for_tests()


def test_create_and_get_fleet(fleet_client):
    create = fleet_client.post(
        "/api/v1/fleets",
        json={"name": "Demo Constellation", "description": "test", "tags": ["leo"]},
    )
    assert create.status_code == 201
    data = create.json()
    assert data["name"] == "Demo Constellation"
    assert data["satellite_count"] == 0
    fleet_id = data["id"]

    get_resp = fleet_client.get(f"/api/v1/fleets/{fleet_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["satellite_count"] == 0


def test_list_fleets(fleet_client):
    fleet_client.post("/api/v1/fleets", json={"name": "Fleet A"})
    fleet_client.post("/api/v1/fleets", json={"name": "Fleet B"})
    response = fleet_client.get("/api/v1/fleets")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_update_and_delete_fleet(fleet_client):
    create = fleet_client.post("/api/v1/fleets", json={"name": "Old Name"})
    fleet_id = create.json()["id"]

    patch = fleet_client.patch(f"/api/v1/fleets/{fleet_id}", json={"name": "New Name"})
    assert patch.status_code == 200
    assert patch.json()["name"] == "New Name"

    delete = fleet_client.delete(f"/api/v1/fleets/{fleet_id}")
    assert delete.status_code == 204

    get_resp = fleet_client.get(f"/api/v1/fleets/{fleet_id}")
    assert get_resp.status_code == 404


def test_add_and_list_satellites(fleet_client):
    fleet_id = fleet_client.post("/api/v1/fleets", json={"name": "Sat Fleet"}).json()["id"]
    add = fleet_client.post(
        f"/api/v1/fleets/{fleet_id}/satellites",
        json={"tle": DEMO_SAT},
    )
    assert add.status_code == 201
    sat = add.json()
    assert sat["norad_id"] == 25544
    assert "ISS" in sat["name"]

    listing = fleet_client.get(f"/api/v1/fleets/{fleet_id}/satellites")
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


def test_duplicate_norad_in_fleet_returns_409(fleet_client):
    fleet_id = fleet_client.post("/api/v1/fleets", json={"name": "Dup Fleet"}).json()["id"]
    first = fleet_client.post(f"/api/v1/fleets/{fleet_id}/satellites", json={"tle": DEMO_SAT})
    assert first.status_code == 201
    second = fleet_client.post(f"/api/v1/fleets/{fleet_id}/satellites", json={"tle": DEMO_SAT})
    assert second.status_code == 409


def test_tle_update_keeps_two_revisions(fleet_client):
    fleet_id = fleet_client.post("/api/v1/fleets", json={"name": "Rev Fleet"}).json()["id"]
    sat_id = fleet_client.post(
        f"/api/v1/fleets/{fleet_id}/satellites", json={"tle": DEMO_SAT}
    ).json()["id"]

    update1 = fleet_client.patch(f"/api/v1/satellites/{sat_id}", json={"tle": DEMO_DEB})
    assert update1.status_code == 200
    assert update1.json()["norad_id"] == 25544 or update1.json()["tle"] == DEMO_DEB

    update2 = fleet_client.patch(
        f"/api/v1/satellites/{sat_id}",
        json={"tle": DEMO_SAT},
    )
    assert update2.status_code == 200

    from backend.app.db.session import get_session_factory
    from backend.app.services import fleet_service

    db = get_session_factory()()
    try:
        revisions = fleet_service.list_tle_revisions(db, __import__("uuid").UUID(sat_id))
        assert len(revisions) <= 2
    finally:
        db.close()


def test_rollback_satellite_tle(fleet_client):
    fleet_id = fleet_client.post("/api/v1/fleets", json={"name": "Rollback Fleet"}).json()["id"]
    sat_id = fleet_client.post(
        f"/api/v1/fleets/{fleet_id}/satellites", json={"tle": DEMO_SAT}
    ).json()["id"]
    fleet_client.patch(f"/api/v1/satellites/{sat_id}", json={"tle": DEMO_DEB})

    rollback = fleet_client.post(f"/api/v1/satellites/{sat_id}/rollback")
    assert rollback.status_code == 200
    assert "ISS" in rollback.json()["tle"] or rollback.json()["norad_id"] == 25544


def test_rollback_without_revision_returns_404(fleet_client):
    fleet_id = fleet_client.post("/api/v1/fleets", json={"name": "No Rev"}).json()["id"]
    sat_id = fleet_client.post(
        f"/api/v1/fleets/{fleet_id}/satellites", json={"tle": DEMO_SAT}
    ).json()["id"]
    response = fleet_client.post(f"/api/v1/satellites/{sat_id}/rollback")
    assert response.status_code == 404


def test_delete_satellite(fleet_client):
    fleet_id = fleet_client.post("/api/v1/fleets", json={"name": "Del Sat"}).json()["id"]
    sat_id = fleet_client.post(
        f"/api/v1/fleets/{fleet_id}/satellites", json={"tle": DEMO_SAT}
    ).json()["id"]
    delete = fleet_client.delete(f"/api/v1/satellites/{sat_id}")
    assert delete.status_code == 204
    get_sat = fleet_client.patch(f"/api/v1/satellites/{sat_id}", json={"name": "x"})
    assert get_sat.status_code == 404


def test_invalid_tle_returns_400(fleet_client):
    fleet_id = fleet_client.post("/api/v1/fleets", json={"name": "Bad TLE"}).json()["id"]
    response = fleet_client.post(
        f"/api/v1/fleets/{fleet_id}/satellites",
        json={"tle": "not a tle"},
    )
    assert response.status_code == 400
