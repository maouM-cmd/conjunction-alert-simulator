# Release v1.35.0 — Phase 10AB

**日付:** 2026-06-28

## 概要

10AA でスコープ外とした breach sticky 上書きを実装。手動設定を `sync_breaches` から保護し、解除 API で自動同期に復帰。

## 変更

- `ALERTMANAGER_BREACH_STATE_STICKY_OVERRIDE_ENABLED` — sticky 上書き opt-in
- `PUT` に `sticky` フラグ（default true）
- `DELETE /api/v1/ops/prometheus/alertmanager/breach-states/sticky` — sticky 解除
- `sync_breaches` — sticky 行はスキップ
- Ops UI — sticky バッジ + 「自動同期」ボタン

## テスト

333 passed（+3）

## 関連

- [requirements-phase10ab.md](requirements-phase10ab.md)
