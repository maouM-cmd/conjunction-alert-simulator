# Release Notes — v1.42.0 (Phase 10AI)

**日付:** 2026-06-28

## 概要

Prometheus reload リトライ + Celery フォールバック、retention CSV エクスポート、breach 履歴日次集計 API を追加。

## 追加

- `reload_prometheus` — `PROMETHEUS_RELOAD_MAX_RETRIES` による同期リトライ
- `PROMETHEUS_RELOAD_CELERY_FALLBACK` — 失敗時 Celery `prometheus_reload` タスク enqueue
- `POST /api/v1/ops/prometheus/reload` — 手動 reload（管理者）
- `GET breach-history-settings?format=csv` — retention CSV
- `GET history/summary` — 日次集計（total / breaching_count）
- Ops UI — reload queued 表示、retention CSV、日次 summary テーブル

## 環境変数

| 変数 | default | 説明 |
|------|---------|------|
| `PROMETHEUS_RELOAD_MAX_RETRIES` | 3 | 同期 POST 回数 |
| `PROMETHEUS_RELOAD_CELERY_FALLBACK` | false | 全リトライ失敗時 Celery enqueue |

## テスト

377 tests PASS（+7 from v1.41.0）
