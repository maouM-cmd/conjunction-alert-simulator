# Release v1.31.0 — Phase 10X

**日付:** 2026-06-28

## 概要

Alertmanager breach 状態の DB 永続化と、Redis 共有時の metrics + Celery dual push を実装。

## 変更

- `ALERTMANAGER_PUSH_DB_STATE_ENABLED=true` — PostgreSQL `fleet_alert_breach_states` で breach 状態永続化
- store 優先順位: Redis > DB > in-memory
- Celery ON + `ALERTMANAGER_PUSH_REDIS_STATE_ENABLED=true` 時、`/metrics` scrape からも `sync_breaches` 実行

## テスト

313 passed（+5）

## 関連

- [requirements-phase10x.md](requirements-phase10x.md)
