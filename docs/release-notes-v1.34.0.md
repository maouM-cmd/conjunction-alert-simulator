# Release v1.34.0 — Phase 10AA

**日付:** 2026-06-28

## 概要

10Z でスコープ外とした breach 横断一覧と手動上書きを実装。

## 変更

- `GET /api/v1/ops/prometheus/alertmanager/breach-states` — `fleet_id` 省略で管理者横断一覧
- `PUT /api/v1/ops/prometheus/alertmanager/breach-states` — `ALERTMANAGER_BREACH_STATE_MANUAL_OVERRIDE_ENABLED` 時の手動上書き
- 監査 `alert.breach_state_manual_override`
- Ops UI — 全艦隊 breach テーブル、手動 breaching/ok ボタン

## テスト

330 passed（+6）

## 関連

- [requirements-phase10aa.md](requirements-phase10aa.md)
