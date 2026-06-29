"""Shared Space-Track.org HTTP client with session auth."""

from __future__ import annotations

import os

import httpx

from backend.app.services.spacetrack_rate_limiter import acquire_spacetrack_slot

LOGIN_URL = "https://www.space-track.org/ajaxauth/login"
BASE_URL = "https://www.space-track.org"


def has_spacetrack_credentials() -> bool:
    return bool(os.getenv("SPACE_TRACK_USER") and os.getenv("SPACE_TRACK_PASSWORD"))


def _throttle() -> None:
    acquire_spacetrack_slot()


def login(client: httpx.Client) -> None:
    user = os.getenv("SPACE_TRACK_USER", "")
    password = os.getenv("SPACE_TRACK_PASSWORD", "")
    response = client.post(
        LOGIN_URL,
        data={"identity": user, "password": password},
        timeout=30.0,
    )
    response.raise_for_status()
    if "Login failed" in response.text:
        raise RuntimeError("Space-Track login failed")


def get_json(path: str) -> list[dict]:
    """GET JSON from Space-Track (path starts with /basicspacedata/...)."""
    if not has_spacetrack_credentials():
        raise RuntimeError("Space-Track credentials not configured")

    url = f"{BASE_URL}{path}" if path.startswith("/") else f"{BASE_URL}/{path}"
    _throttle()
    with httpx.Client(follow_redirects=True, timeout=120.0) as client:
        login(client)
        _throttle()
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise RuntimeError("Space-Track returned unexpected CDM response")
        return data


def get_text(url: str) -> str:
    """GET plain text (e.g. TLE catalog) after login."""
    if not has_spacetrack_credentials():
        raise RuntimeError("Space-Track credentials not configured")

    _throttle()
    with httpx.Client(follow_redirects=True, timeout=120.0) as client:
        login(client)
        _throttle()
        response = client.get(url)
        response.raise_for_status()
        return response.text.strip()
