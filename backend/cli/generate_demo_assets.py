"""Generate demo PNG/GIF assets for README from API data."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import matplotlib.pyplot as plt
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
        0.68,
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
        "Phase 4: Pc (Foster / Alfriend) | CDM compare | Batch | Docker | Webhook\n"
        "ISS vs COSMOS 2251 DEB | SGP4 + FastAPI + CesiumJS",
        ha="center",
        va="center",
        fontsize=11,
        color="#9fb0d0",
    )
    fig.savefig(out_path, dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)


def conjunction_table(events: list, out_path: Path, advanced: bool = False) -> None:
    fig, ax = plt.subplots(figsize=(10, 6), facecolor="#0b1020")
    ax.set_facecolor("#11182b")
    ax.axis("off")
    mode = "Advanced Pc (Alfriend encounter plane)" if advanced else "Foster Pc"
    lines = [f"Top conjunction events — {mode} (threshold 50 km):", ""]
    for e in events[:8]:
        pc = e.get("pc", 0)
        method = e.get("pc_method_used", "foster")
        cov = e.get("covariance_source")
        cov_note = f" [{cov}]" if cov else ""
        if method == "encounter_advanced":
            foster = e.get("pc_foster")
            foster_txt = f" / Foster {foster:.2e}" if foster is not None else ""
            lines.append(
                f"- {e['debris_name']} | {e['miss_distance_km']:.2f} km | "
                f"Pc {pc:.2e}{foster_txt}{cov_note} | {e['risk_level']}"
            )
        else:
            lines.append(
                f"- {e['debris_name']} | {e['miss_distance_km']:.2f} km | "
                f"Pc {pc:.2e} | {e['risk_level']}"
            )
    ax.text(
        0.05,
        0.95,
        "\n".join(lines),
        ha="left",
        va="top",
        fontsize=9,
        color="#e8edf7",
        family="monospace",
    )
    fig.savefig(out_path, dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)


def cdm_compare_card(compare: dict, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 6), facecolor="#0b1020")
    ax.set_facecolor("#11182b")
    ax.axis("off")
    pm = compare.get("pc_methods") or {}
    lines = [
        "CDM vs CAS compare (encounter plane)",
        "",
        f"CDM Pc:        {compare['cdm'].get('pc')}",
        f"CAS Pc:        {compare['cas'].get('pc')}",
        f"Miss CDM/CAS:  {compare['cdm'].get('miss_distance_km')} / "
        f"{compare['cas'].get('miss_distance_km')} km",
        f"Sigma source:  {compare.get('sigma_source')}",
        "",
        f"Foster:        {pm.get('foster')}",
        f"Alfriend:      {pm.get('alfriend')}",
        f"Monte Carlo:   {pm.get('monte_carlo')}",
        f"Method used:   {compare.get('pc_method_used')}",
    ]
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
    cdm_text = (SAMPLES / "example.cdm").read_text(encoding="utf-8")

    with httpx.Client(timeout=120.0) as client:
        conj = client.post(
            f"{API}/api/v1/conjunctions",
            json={
                "tle": sat_tle,
                "threshold_km": 50,
                "duration_days": 7,
                "use_advanced_pc": True,
            },
        )
        conj.raise_for_status()
        conj_data = conj.json()

        sat_orbit = client.post(
            f"{API}/api/v1/orbit",
            json={"tle": sat_tle, "duration_days": 7, "step_minutes": 5},
        ).json()
        deb_orbit = client.post(
            f"{API}/api/v1/orbit",
            json={"tle": deb_tle, "duration_days": 7, "step_minutes": 5},
        ).json()
        first = conj_data["conjunctions"][0]
        maneuver = client.post(
            f"{API}/api/v1/maneuver/preview",
            json={
                "satellite_tle": sat_tle,
                "debris_tle": first["debris_tle"],
                "direction": "prograde",
                "delta_v_ms": 0.1,
            },
        ).json()
        cdm_compare = client.post(
            f"{API}/api/v1/cdm/compare",
            json={
                "cdm_text": cdm_text,
                "satellite_tle": sat_tle,
                "debris_tle": deb_tle,
                "duration_days": 7,
                "step_minutes": 1,
            },
        ).json()

    p1 = OUT_DIR / "01-initial.png"
    p2 = OUT_DIR / "02-conjunctions.png"
    p3 = OUT_DIR / "03-orbit-tca.png"
    p4 = OUT_DIR / "04-maneuver.png"
    p5 = OUT_DIR / "05-cdm-compare.png"

    title_card(p1)
    conjunction_table(conj_data["conjunctions"], p2, advanced=True)
    plot_orbits(
        sat_orbit["points"],
        deb_orbit["points"],
        f"Orbits: {sat_orbit['name']} vs {deb_orbit['name']}",
        p3,
    )
    maneuver_card(maneuver["before"], maneuver["after"], p4)
    cdm_compare_card(cdm_compare, p5)
    make_gif([p1, p2, p3, p4, p5], OUT_DIR / "demo.gif")

    meta = {
        "conjunction_count": len(conj_data["conjunctions"]),
        "closest_km": first["miss_distance_km"],
        "pc_method_used": first.get("pc_method_used"),
        "generated": [str(p.name) for p in (p1, p2, p3, p4, p5, OUT_DIR / "demo.gif")],
    }
    (OUT_DIR / "assets-meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
