# Release v1.21.0 — Phase 10N

**日付:** 2026-06-28

## 概要

10H/10J の global API SLO を拡張し、fleet スコープ API Key リクエスト単位の可用性計測・Ops 表示・DB 永続化を opt-in で追加。

## 変更

- `SLA_FLEET_API_SLO_ENABLED=true` で艦隊別 1h バケット集計
- `GET /ops/sla` — 各艦隊に `fleet_api_*` フィールド
- `GET /ops/sla/api-history?fleet_id=` — fleet 日次履歴
- Prometheus per-fleet Gauge
- global SLO は既存維持

## テスト

240 passed

## 関連

- [requirements-phase10n.md](requirements-phase10n.md)
