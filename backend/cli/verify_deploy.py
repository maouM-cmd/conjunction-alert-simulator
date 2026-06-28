"""Remote deploy smoke test for /health and /app/."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def _get(url: str, timeout: float) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "CAS-verify-deploy/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def verify(base_url: str, timeout: float = 120.0) -> None:
    base = base_url.rstrip("/")
    errors: list[str] = []

    health_url = f"{base}/health"
    try:
        status, body = _get(health_url, timeout)
        if status != 200:
            errors.append(f"/health が HTTP {status} を返しました")
        else:
            data = json.loads(body)
            if data.get("status") != "ok":
                errors.append(f"/health の status が ok ではありません: {data!r}")
            else:
                print(f"OK  /health → {health_url}")
    except urllib.error.HTTPError as exc:
        errors.append(f"/health が失敗しました: HTTP {exc.code} ({health_url})")
    except urllib.error.URLError as exc:
        errors.append(f"/health に接続できません: {exc.reason} ({health_url})")
    except json.JSONDecodeError as exc:
        errors.append(f"/health の JSON が不正です: {exc}")

    app_url = f"{base}/app/"
    try:
        status, body = _get(app_url, timeout)
        if status != 200:
            errors.append(f"/app/ が HTTP {status} を返しました")
        elif "Conjunction Alert Simulator" not in body:
            errors.append("/app/ に UI タイトルが含まれていません")
        else:
            print(f"OK  /app/   → {app_url}")
    except urllib.error.HTTPError as exc:
        errors.append(f"/app/ が失敗しました: HTTP {exc.code} ({app_url})")
    except urllib.error.URLError as exc:
        errors.append(f"/app/ に接続できません: {exc.reason} ({app_url})")

    if errors:
        print("デプロイ検証に失敗しました:", file=sys.stderr)
        for msg in errors:
            print(f"  - {msg}", file=sys.stderr)
        sys.exit(1)

    print("デプロイ検証 OK")


def main() -> None:
    parser = argparse.ArgumentParser(description="CAS リモートデプロイのスモークテスト")
    parser.add_argument(
        "--url",
        required=True,
        help="ベース URL（例: https://conjunction-alert-simulator.onrender.com）",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="HTTP タイムアウト秒（cold start 用に長め、デフォルト 120）",
    )
    args = parser.parse_args()
    verify(args.url, timeout=args.timeout)


if __name__ == "__main__":
    main()
