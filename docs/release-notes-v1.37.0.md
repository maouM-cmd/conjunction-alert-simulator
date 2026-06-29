# Release v1.37.0 — Phase 10AD

**日付:** 2026-06-28

## 概要

10AC でスコープ外とした管理者横断 breach 履歴と retention purge を実装。Ops UI から全艦隊の履歴参照と CSV エクスポートが可能。

## 変更

- `GET breach-states/history` — `fleet_id` 省略で管理者横断（`fleet_name` 付き）
- `ALERTMANAGER_BREACH_HISTORY_RETENTION_DAYS` — default 90 日
- Celery `purge_old_breach_history` — 日次古い行削除
- Ops UI — 全艦隊 breach 履歴テーブル + CSV

## テスト

346 passed（+6）

## 関連

- [requirements-phase10ad.md](requirements-phase10ad.md)
