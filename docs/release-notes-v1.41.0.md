# Release Notes — v1.41.0 (Phase 10AH)

**日付:** 2026-06-28

## 概要

Prometheus reload webhook、retention 横断 bulk 設定、breach 履歴日付 range フィルタを追加。

## 追加

- apply 成功後の `PROMETHEUS_RELOAD_URL` POST reload（opt-in）
- `GET /api/v1/ops/fleets/breach-history-settings` — 管理者 retention 一覧
- `PATCH /api/v1/ops/fleets/breach-history-settings/bulk` — 一括更新
- `GET history?since=&until=` — 日付 range フィルタ
- Ops UI — retention 一覧/bulk、since/until、reload ステータス

## 環境変数

| 変数 | 説明 |
|------|------|
| `PROMETHEUS_RELOAD_URL` | apply 後に POST する reload URL |
| `PROMETHEUS_RELOAD_BASIC_AUTH_USER` | 任意 Basic Auth |
| `PROMETHEUS_RELOAD_BASIC_AUTH_PASSWORD` | 任意 Basic Auth |

## テスト

370 tests PASS（+7 from v1.40.0）
