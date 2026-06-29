# CAS v1.17.0 — Phase 10J SLO DB Persistence

**Conjunction Alert Simulator** v1.17.0 — API 可用性 SLO の 1h バケットを DB に永続化し、再起動耐性と日次履歴を提供。

## ハイライト

- **Phase 10J** — `api_slo_hourly_buckets` テーブル + write-through upsert
- 再起動後もローリング窓 API 可用性を維持（`SLA_API_PERSIST_ENABLED=true`）
- `GET /api/v1/ops/sla/api-history?days=30` — UTC 日次 rollup
- Ops UI: 7 日平均トレンド行
- retention prune（default 90 日）

## 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `SLA_API_PERSIST_ENABLED` | `false` | DB 永続化 ON |
| `SLA_API_RETENTION_DAYS` | `90` | 古いバケット削除 |
| `SLA_API_TARGET_PERCENT` | `99.9` | SLO 目標（10H 継続） |
| `SLA_API_ROLLING_WINDOW_HOURS` | `720` | ローリング窓（10H 継続） |

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 10J 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase10j.md |

## 使い方

`DATABASE_URL` + `SLA_API_PERSIST_ENABLED=true` を設定すると、HTTP メトリクスミドルウェアが 1h バケットを DB に write-through。`/metrics` scrape 時に hydrate + prune。Ops ダッシュボードで 7 日トレンドを確認。

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [v1.16.0 — Phase 10I OIDC SSO](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.16.0)

**License:** MIT
