"""Smoke tests for deployable app surface."""

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = PROJECT_ROOT / "docs" / "demo"

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


def test_demo_assets_present():
    """README demo.gif link should resolve to committed portfolio assets."""
    assert (DEMO_DIR / "demo.gif").is_file()
    for name in (
        "01-initial.png",
        "02-conjunctions.png",
        "03-orbit-tca.png",
        "04-maneuver.png",
        "05-cdm-compare.png",
    ):
        assert (DEMO_DIR / name).is_file()
