# Release Notes — v1.44.0 (Phase 10AK)

**日付:** 2026-06-28

## 概要

管理者 per-fleet summary 内訳、retention CSV import dry-run、Prometheus reload 手動 UI を追加。

## 追加

- `GET history/summary?group_by=fleet` — 日次×艦隊集計
- `POST breach-history-settings/import?dry_run=true` — preview 応答
- Ops UI — per-fleet summary テーブル、dry-run プレビュー、Prometheus reload ボタン

## テスト

391 tests PASS（+7 from v1.43.0）
