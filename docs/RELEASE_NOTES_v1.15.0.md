# CAS v1.15.0 — Phase 10H API 99.9% SLO Dashboard

**Conjunction Alert Simulator** v1.15.0 — ローリング窓 API 可用性 SLO を Ops API/UI と Prometheus で可視化。

## ハイライト

- **Phase 10H** — API **99.9%** 可用性 SLO（5xx ベース、1h バケット・720h 窓）
- `cas_api_availability_ratio` / `cas_api_slo_ok` Prometheus Gauge
- `GET /api/v1/ops/sla` — API SLO フィールド追加
- Ops UI: API availability OK/BREACH 行

## 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `SLA_API_TARGET_PERCENT` | `99.9` | API SLO 目標（%） |
| `SLA_API_ROLLING_WINDOW_HOURS` | `720` | ローリング窓（30 日） |

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 10H 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase10h.md |

## 使い方

Ops タブで艦隊を選択 → summary に **Screening lag** に加え **API availability** 行を確認。Prometheus で `cas_api_availability_ratio` / `cas_api_slo_ok` を scrape。

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [v1.14.0 — Phase 10G Auto Mitigation Plan](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.14.0)

**License:** MIT
