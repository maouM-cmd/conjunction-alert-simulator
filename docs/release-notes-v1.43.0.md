# Release Notes — v1.43.0 (Phase 10AJ)

**日付:** 2026-06-28

## 概要

summary CSV エクスポート、retention CSV インポート、Prometheus reload Celery タスクポーリング UI を追加。

## 追加

- `GET history/summary?format=csv` — 日次集計 CSV
- `POST /api/v1/ops/fleets/breach-history-settings/import` — retention CSV インポート
- `reload_task_id` + `GET /api/v1/ops/prometheus/reload/tasks/{task_id}`
- Ops UI — summary CSV、retention インポート、reload ポーリング

## テスト

384 tests PASS（+7 from v1.42.0）
