# CAS Phase 10J — 要件定義書

**版:** 10J  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10j.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第十フェーズ。Phase 10H のインメモリ API 可用性バケットを PostgreSQL に永続化し、再起動耐性と日次履歴を提供する。

| 変更箇所 | 内容 |
|---------|------|
| DB | `api_slo_hourly_buckets` |
| Service | `slo_persistence_service` write-through |
| API | `GET /api/v1/ops/sla/api-history` |
| UI | Ops 7 日 API SLO トレンド |

---

## 2. 機能要件

### FR-10J-1: 1h バケット永続化

- `hour_epoch`, `request_total`, `errors_5xx`

### FR-10J-2: write-through

- `record_http_status` 時に DB upsert

### FR-10J-3: 再起動耐性

- persist ON 時 `compute_api_availability` は DB から集計

### FR-10J-4: 日次履歴 API

- `GET /api/v1/ops/sla/api-history?days=30`

### FR-10J-5: Ops UI

- 7 日トレンド行

### FR-10J-6: 保持

- `SLA_API_RETENTION_DAYS`（default 90）で prune

---

## 3. 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `SLA_API_PERSIST_ENABLED` | `false` | DB 永続化 |
| `SLA_API_RETENTION_DAYS` | `90` | バケット保持 |

---

## 4. スコープ外

- 共分散伝播強化、PagerDuty、fleet 別 API SLO

---

## 5. 成功条件

1. persist ON で再起動後も可用性維持
2. api-history + Ops UI 表示
3. pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 10H](requirements-phase10h.md)
- [Phase 10I](requirements-phase10i.md)
