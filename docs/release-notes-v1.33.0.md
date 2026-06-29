# Release v1.33.0 — Phase 10Z

**日付:** 2026-06-28

## 概要

10X で先送りした DB 共有 dual push を拡張し、Ops パネルで Alertmanager breach 状態を可視化。

## 変更

- `should_sync_breaches_on_metrics_scrape()` — Celery ON + `ALERTMANAGER_PUSH_DB_STATE_ENABLED` でも `/metrics` から `sync_breaches`
- `GET /api/v1/ops/prometheus/alertmanager/breach-states?fleet_id=` — 艦隊の breach 状態（backend: redis/db/memory）
- Ops UI — breach 状態セクション（`CASFleetOpenAlertsHigh` / `CASFleetHighRiskOpenAlerts`）

## テスト

324 passed（+5）

## 関連

- [requirements-phase10z.md](requirements-phase10z.md)
