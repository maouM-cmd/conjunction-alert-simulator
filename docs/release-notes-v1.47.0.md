# Release v1.47.0 — Phase 10AN

**日付:** 2026-06-28

## 概要

reload 履歴 Redis TTL、retention dry-run preview CSV、per-fleet summary limit/offset。

## Added

- reload 履歴 Redis `EXPIRE` + エントリ TTL フィルタ
- `POST import?dry_run=true&format=csv` + Ops dry-run CSV ボタン
- `GET summary?group_by=fleet&limit=&offset=` + Ops 表示件数

## env

- `PROMETHEUS_RELOAD_HISTORY_REDIS_TTL_SECONDS`（default 604800、0 で無効）
