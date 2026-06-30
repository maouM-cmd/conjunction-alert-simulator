# Release v1.46.0 — Phase 10AM

**日付:** 2026-06-28

## 概要

reload 履歴 Redis 永続化、retention dry-run 折りたたみ、per-fleet summary 艦隊名フィルタ。

## Added

- Prometheus reload 履歴 Redis LIST 永続化（in-memory フォールバック）
- `preview[].will_change` + Ops dry-run 変更行のみ UI
- `GET summary?group_by=fleet&fleet_name_contains=...` + Ops 艦隊名フィルタ

## env

- `PROMETHEUS_RELOAD_HISTORY_REDIS_ENABLED`（default: Redis 設定時 true）
