# Release v1.30.0 — Phase 10W

**日付:** 2026-06-28

## 概要

Alertmanager silence の艦隊一括削除 API と Ops UI 上の silence 管理を実装。

## 変更

- `DELETE /api/v1/ops/prometheus/alertmanager/silences?fleet_id=` — fleet 単位 bulk 削除（optional `alertname`）
- Ops UI「Alertmanager Silences」— 一覧・作成・行削除・艦隊一括削除
- silences 無効時は UI で非エラー表示

## テスト

308 passed（+6）

## 関連

- [requirements-phase10w.md](requirements-phase10w.md)
