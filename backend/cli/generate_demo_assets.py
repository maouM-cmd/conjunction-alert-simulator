"""Generate demo PNG/GIF assets for README from API data."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLES = PROJECT_ROOT / "samples"
OUT_DIR = PROJECT_ROOT / "docs" / "demo"
API = "http://127.0.0.1:8000"


def _setup_japanese_font() -> None:
    for name in ("Yu Gothic UI", "Meiryo", "MS Gothic", "DejaVu Sans"):
        if any(f.name == name for f in font_manager.fontManager.ttflist):
            plt.rcParams["font.family"] = name
            return


def plot_orbits(sat_points: list, deb_points: list, title: str, out_path: Path) -> None:
    sx = [p["position_km"]["x"] for p in sat_points]
    sy = [p["position_km"]["y"] for p in sat_points]
    sz = [p["position_km"]["z"] for p in sat_points]
    dx = [p["position_km"]["x"] for p in deb_points]
    dy = [p["position_km"]["y"] for p in deb_points]
    dz = [p["position_km"]["z"] for p in deb_points]

    fig = plt.figure(figsize=(10, 6), facecolor="#0b1020")
    ax = fig.add_subplot(111, projection="3d", facecolor="#11182b")
    ax.plot(sx, sy, sz, color="#4da3ff", linewidth=1.2, label="Satellite")
    ax.plot(dx, dy, dz, color="#ff6b6b", linewidth=1.2, label="Debris")
    ax.set_title(title, color="#e8edf7", fontsize=12)
    ax.legend(loc="upper right")
    ax.set_xlabel("X (km)", color="#9fb0d0")
    ax.set_ylabel("Y (km)", color="#9fb0d0")
    ax.set_zlabel("Z (km)", color="#9fb0d0")
    ax.tick_params(colors="#9fb0d0")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)


def title_card(out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 6), facecolor="#0b1020")
    ax.set_facecolor("#11182b")
    ax.axis("off")
    ax.text(
        0.5,
        0.62,
        "Conjunction Alert Simulator",
        ha="center",
        va="center",
        fontsize=22,
        color="#e8edf7",
        weight="bold",
    )
    ax.text(
        0.5,
        0.42,
        "ISS vs COSMOS 2251 DEB\n7-day conjunction scan | SGP4 + FastAPI + CesiumJS",
        ha="center",
        va="center",
        fontsize=12,
        color="#9fb0d0",
    )
    fig.savefig(out_path, dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)


def conjunction_table(events: list, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 6), facecolor="#0b1020")
    ax.set_facecolor("#11182b")
    ax.axis("off")
    lines = ["Top conjunction events (threshold 50 km):", ""]
    for e in events[:8]:
        lines.append(
            f"- {e['debris_name']} | {e['miss_distance_km']:.2f} km | "
            f"{e['risk_level']} | TCA {e['tca'][:19]}Z"
        )
    ax.text(
        0.05,
        0.95,
        "\n".join(lines),
        ha="left",
        va="top",
        fontsize=10,
        color="#e8edf7",
        family="monospace",
    )
    fig.savefig(out_path, dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)


def maneuver_card(before: dict, after: dict, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 6), facecolor="#0b1020")
    ax.set_facecolor("#11182b")
    ax.axis("off")
    text = (
        "Maneuver preview (prograde 0.1 m/s)\n\n"
        f"Before: {before['miss_distance_km']:.3f} km\n"
        f"After:  {after['miss_distance_km']:.3f} km\n\n"
        f"Delta miss distance: {after['miss_distance_km'] - before['miss_distance_km']:+.3f} km"
    )
    ax.text(0.5, 0.5, text, ha="center", va="center", fontsize=14, color="#e8edf7")
    fig.savefig(out_path, dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)


def make_gif(frames: list[Path], out_path: Path, duration_ms: int = 800) -> None:
    images = [Image.open(p).convert("P", palette=Image.ADAPTIVE) for p in frames]
    images[0].save(
        out_path,
        save_all=True,
        append_images=images[1:],
        duration=duration_ms,
        loop=0,
    )


def main() -> None:
    _setup_japanese_font()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    sat_tle = (SAMPLES / "demo-satellite.tle").read_text(encoding="utf-8")
    deb_tle = (SAMPLES / "demo-debris.tle").read_text(encoding="utf-8")

    with httpx.Client(timeout=120.0) as client:
        conj = client.post(
            f"{API}/api/v1/conjunctions",
            json={"tle": sat_tle, "threshold_km": 50, "duration_days": 7},
        ).json()
        sat_orbit = client.post(
            f"{API}/api/v1/orbit",
            json={"tle": sat_tle, "duration_days": 7, "step_minutes": 5},
        ).json()
        deb_orbit = client.post(
            f"{API}/api/v1/orbit",
            json={"tle": deb_tle, "duration_days": 7, "step_minutes": 5},
        ).json()
        first = conj["conjunctions"][0]
        maneuver = client.post(
            f"{API}/api/v1/maneuver/preview",
            json={
                "satellite_tle": sat_tle,
                "debris_tle": first["debris_tle"],
                "direction": "prograde",
                "delta_v_ms": 0.1,
            },
        ).json()

    p1 = OUT_DIR / "01-initial.png"
    p2 = OUT_DIR / "02-conjunctions.png"
    p3 = OUT_DIR / "03-orbit-tca.png"
    p4 = OUT_DIR / "04-maneuver.png"

    title_card(p1)
    conjunction_table(conj["conjunctions"], p2)
    plot_orbits(
        sat_orbit["points"],
        deb_orbit["points"],
        f"Orbits: {sat_orbit['name']} vs {deb_orbit['name']}",
        p3,
    )
    maneuver_card(maneuver["before"], maneuver["after"], p4)
    make_gif([p1, p2, p3, p4], OUT_DIR / "demo.gif")

    meta = {
        "conjunction_count": len(conj["conjunctions"]),
        "closest_km": first["miss_distance_km"],
        "generated": [str(p.name) for p in (p1, p2, p3, p4, OUT_DIR / "demo.gif")],
    }
    (OUT_DIR / "assets-meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
