# CAS v1.6.0 — Phase 9D Scale-Out

**Conjunction Alert Simulator** v1.6.0 — 10,000 衛星艦隊と worker 水平スケール。

## ハイライト

- **Phase 9D** — スクリーニングを 50 sat/chunk の Celery ジョブに分割（親 run が N チャンクを orchestrate）
- 艦隊上限 **10,000**（`FLEET_MAX_SATELLITES`）、ad-hoc batch API は 25 件のまま
- Space-Track CDM **Redis 共有レートリミット**（マルチ worker 対応）
- **`GET /metrics`** — Prometheus 形式（open alerts、screening runs、Celery queue depth）
- `docker compose up --scale worker=3` で worker 水平スケール

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 9D 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase9d.md |

## デモ

```powershell
docker compose up --build -d --scale worker=3
curl http://localhost:8000/metrics
```

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [v1.5.0 — Phase 9C Alert Ops](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.5.0)

**License:** MIT
