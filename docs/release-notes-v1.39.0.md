# Release v1.39.0 — Phase 10AF

**日付:** 2026-06-28

## 概要

10AE でスコープ外とした per-fleet 履歴 purge、breaching 艦隊 rule フィルタ、Ops UI を実装。

## 変更

- `purge_old_breach_history(fleet_id)` + Celery 艦隊ループ（`by_fleet`）
- `DELETE breach-states/history` — 手動 retention purge
- `GET fleet-alert-rules?breaching_fleets_only=true`
- Ops UI — ルール雛形ダウンロード（yaml/json）

## テスト

356 passed（+4）

## 関連

- [requirements-phase10af.md](requirements-phase10af.md)
