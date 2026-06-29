# Release v1.28.0 — Phase 10U

**日付:** 2026-06-28

## 概要

triage 時の Alertmanager 自動 silence と Celery 定期 breach push を実装。

## 変更

- `ALERTMANAGER_PUSH_CELERY_ENABLED=true` — beat で `sync_fleet_alert_breaches`（default 60s）
- Celery ON 時は `/metrics` scrape から breach push を除外（重複防止）
- `ALERTMANAGER_AUTO_SILENCE_ON_TRIAGE_ENABLED=true` — `acknowledged` / `false_positive` 遷移時に fleet silence
- `fleet_metrics_sync_service.collect_and_export_fleet_metrics`

## テスト

293 passed（+6）

## 関連

- [requirements-phase10u.md](requirements-phase10u.md)
