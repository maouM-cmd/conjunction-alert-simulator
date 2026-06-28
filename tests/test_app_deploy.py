"""Smoke tests for deployable app surface."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "spacetrack_configured" in data
    assert "spacetrack_cdm_available" in data


def test_root_links_to_app():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "/app/"


def test_frontend_mounted():
    response = client.get("/app/", follow_redirects=True)
    assert response.status_code == 200
    assert "Conjunction Alert Simulator" in response.text
