# Release v1.32.0 — Phase 10Y

**日付:** 2026-06-28

## 概要

Alertmanager silence の複数 ID 選択式 bulk 削除 API と Ops UI チェックボックスを実装。

## 変更

- `POST /api/v1/ops/prometheus/alertmanager/silences/bulk-delete` — `{ "silence_ids": [...] }` で選択削除
- Ops UI — チェックボックス列、全選択、「選択した silence を削除」ボタン
- 艦隊全削除（10W）は既存のまま維持

## テスト

319 passed（+6）

## 関連

- [requirements-phase10y.md](requirements-phase10y.md)
