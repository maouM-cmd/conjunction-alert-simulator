# Release Notes — v1.40.0 (Phase 10AG)

**日付:** 2026-06-28

## 概要

艦隊別 breach 履歴 retention 日数、Prometheus ルール雛形のファイル apply、履歴 alertname 複数フィルタを追加。

## 追加

- `fleets.breach_history_retention_days` — 艦隊別 retention override（Alembic 014）
- `effective_retention_days` / per-fleet purge cutoff
- `PATCH /api/v1/ops/fleets/{fleet_id}/breach-history-settings` — 管理者のみ
- `POST /api/v1/ops/prometheus/fleet-alert-rules/apply` — `PROMETHEUS_FLEET_RULES_OUTPUT_PATH` へ atomic 書き込み
- `GET history?alertnames=` — 複数 alertname OR フィルタ
- Ops UI — retention 設定、alertname チェックボックス、ルール apply ボタン

## 環境変数

| 変数 | 説明 |
|------|------|
| `PROMETHEUS_FLEET_RULES_OUTPUT_PATH` | apply 先ファイルパス（未設定時 apply は no-op） |

## テスト

363+ tests PASS（+7 from v1.39.0）
