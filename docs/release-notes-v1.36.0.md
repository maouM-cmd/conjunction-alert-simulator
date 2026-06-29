# Release v1.36.0 — Phase 10AC

**日付:** 2026-06-28

## 概要

10AB でスコープ外とした breaching-only フィルタと breach 変更履歴を実装。Ops UI から履歴参照と CSV エクスポートが可能。

## 変更

- `ALERTMANAGER_BREACH_HISTORY_ENABLED` — breach 履歴 opt-in
- `fleet_alert_breach_history` — sync / manual / sticky_clear 遷移記録
- `GET breach-states?breaching_only=true` — breaching 行のみ
- `GET breach-states/history` — JSON / `format=csv`
- Ops UI — breaching チェックボックス、履歴テーブル、CSV ダウンロード

## テスト

340 passed（+7）

## 関連

- [requirements-phase10ac.md](requirements-phase10ac.md)
