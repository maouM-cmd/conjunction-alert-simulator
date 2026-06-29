# CAS v1.9.0 — Phase 10B SLA Metrics

**Conjunction Alert Simulator** v1.9.0 — FR-9E-4 SLA 目標の計測可能化。

## ハイライト

- **Phase 10B** — スクリーニング lag（24h 目標）を Prometheus + Ops で可視化
- `cas_http_requests_total` — API 可用性 99.5% 監視用 Counter
- `GET /api/v1/ops/sla` — 艦隊ごと OK/OVERDUE
- Ops UI summary に Screening lag 表示

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 10B 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase10b.md |

## 環境変数

```powershell
# .env
SLA_SCREENING_MAX_LAG_HOURS=24
```

## Prometheus 例

```promql
cas_screening_overdue_fleets > 0
```

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [v1.8.0 — Phase 10A COLA Preview](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.8.0)

**License:** MIT
