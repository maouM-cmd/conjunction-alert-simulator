"""CLI for two-body distance propagation prototype."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.app.services.conjunction import find_closest_approach
from backend.app.services.propagator import propagate_orbit
from backend.app.services.tle_parser import parse_tle


def main() -> None:
    parser = argparse.ArgumentParser(description="TLE 2本の7日間接近解析 CLI")
    parser.add_argument("--tle1", required=True, help="衛星 TLE ファイル")
    parser.add_argument("--tle2", required=True, help="デブリ TLE ファイル")
    parser.add_argument("--days", type=float, default=7.0)
    parser.add_argument("--step", type=int, default=1, help="刻み（分）")
    args = parser.parse_args()

    sat = parse_tle(Path(args.tle1).read_text(encoding="utf-8"))
    deb = parse_tle(Path(args.tle2).read_text(encoding="utf-8"))
    start = datetime.now(timezone.utc)

    sat_pts = propagate_orbit(sat, start, args.days, args.step)
    deb_pts = propagate_orbit(deb, start, args.days, args.step)

    result = find_closest_approach(sat_pts, deb_pts)
    output = {
        "satellite": sat.name,
        "debris": deb.name,
        "tca": result.tca.isoformat().replace("+00:00", "Z"),
        "miss_distance_km": round(result.miss_distance_km, 4),
        "relative_velocity_kms": round(result.relative_velocity_kms, 4),
        "samples": len(sat_pts),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
