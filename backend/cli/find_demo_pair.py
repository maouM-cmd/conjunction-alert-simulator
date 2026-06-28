"""Find satellite/debris TLE pair with closest approach for portfolio demo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from datetime import datetime, timezone

from backend.app.services.analysis import run_conjunction_analysis
from backend.app.services.cdm_export import _tca_to_cdm_string
from backend.app.services.tle_parser import parse_tle

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLES_DIR = PROJECT_ROOT / "samples"


def find_demo_pair(satellite_tle_path: Path, scan_threshold_km: float = 500.0) -> dict:
    sat_text = satellite_tle_path.read_text(encoding="utf-8")
    satellite = parse_tle(sat_text)

    print(f"衛星: {satellite.name} - 閾値 {scan_threshold_km} km で接近イベントを探索...")
    result = run_conjunction_analysis(
        sat_text,
        duration_days=7.0,
        threshold_km=scan_threshold_km,
        step_minutes=1,
        use_altitude_prefilter=True,
        use_advanced_pc=True,
    )

    if not result.events:
        raise RuntimeError(
            f"{scan_threshold_km} km 以内の接近イベントが見つかりませんでした。"
            "閾値を広げるか、別の衛星 TLE を試してください。"
        )

    closest = result.events[0]
    recommended = min(50.0, max(5.0, round(closest.miss_distance_km * 1.5, 1)))

    return {
        "satellite_name": satellite.name,
        "satellite_norad_id": satellite.norad_id,
        "debris_name": closest.debris_name,
        "debris_norad_id": closest.debris_norad_id,
        "miss_distance_km": round(closest.miss_distance_km, 4),
        "tca": closest.tca.isoformat().replace("+00:00", "Z"),
        "relative_velocity_kms": round(closest.relative_velocity_kms, 4),
        "risk_level": closest.risk_level,
        "pc": closest.pc,
        "pc_foster": closest.pc_foster,
        "pc_alfriend": closest.pc_alfriend,
        "pc_method_used": closest.pc_method_used,
        "satellite_tle": satellite.text,
        "debris_tle": closest.debris_tle,
        "recommended_threshold_km": recommended,
        "events_within_scan_km": len(result.events),
        "computation_time_ms": result.computation_time_ms,
    }


def sync_example_cdm(meta: dict, cdm_path: Path | None = None) -> None:
    """Align example.cdm TCA/miss with demo-pair metadata."""
    path = cdm_path or SAMPLES_DIR / "example.cdm"
    tca = datetime.fromisoformat(meta["tca"].replace("Z", "+00:00"))
    if tca.tzinfo is None:
        tca = tca.replace(tzinfo=timezone.utc)
    pc = meta.get("pc")
    lines = path.read_text(encoding="utf-8").splitlines()
    updated: list[str] = []
    for line in lines:
        if line.startswith("TCA ="):
            updated.append(f"TCA = {_tca_to_cdm_string(tca)}")
        elif line.startswith("MISS_DISTANCE ="):
            updated.append(f"MISS_DISTANCE = {meta['miss_distance_km']:.2f} km")
        elif line.startswith("RELATIVE_SPEED ="):
            updated.append(f"RELATIVE_SPEED = {meta['relative_velocity_kms']:.4f} km/s")
        elif line.startswith("COLLISION_PROBABILITY =") and pc is not None:
            updated.append(f"COLLISION_PROBABILITY = {pc:.6e}")
        elif line.startswith("SAT2_OBJECT ="):
            updated.append(f"SAT2_OBJECT = {meta['debris_name']}")
        else:
            updated.append(line)
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="デモ用 TLE ペアを探索して samples/ に保存")
    parser.add_argument(
        "--satellite",
        default=str(SAMPLES_DIR / "iss.tle"),
        help="衛星 TLE ファイル",
    )
    parser.add_argument("--scan-threshold", type=float, default=500.0)
    parser.add_argument("--out-dir", default=str(SAMPLES_DIR))
    args = parser.parse_args()

    result = find_demo_pair(Path(args.satellite), scan_threshold_km=args.scan_threshold)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "demo-satellite.tle").write_text(result["satellite_tle"] + "\n", encoding="utf-8")
    (out_dir / "demo-debris.tle").write_text(result["debris_tle"] + "\n", encoding="utf-8")

    meta = {k: v for k, v in result.items() if k not in ("satellite_tle", "debris_tle")}
    (out_dir / "demo-pair.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    sync_example_cdm(meta, out_dir / "example.cdm")

    print(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"\n保存: {out_dir / 'demo-satellite.tle'}")
    print(f"保存: {out_dir / 'demo-debris.tle'}")


if __name__ == "__main__":
    main()
