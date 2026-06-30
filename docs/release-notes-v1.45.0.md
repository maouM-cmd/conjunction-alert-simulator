# Release v1.45.0 — Phase 10AL

**日付:** 2026-06-28

## 概要

Ops UI 仕上げ: per-fleet summary CSV ダウンロード、retention dry-run プレビュー詳細テーブル、Prometheus reload 履歴一覧。

## Added

- `GET /api/v1/ops/prometheus/reload/history` — 直近 reload 履歴（in-memory）
- Ops UI — fleet summary CSV ボタン
- Ops UI — retention dry-run preview テーブル
- Ops UI — Prometheus reload 履歴テーブル

## env

- `PROMETHEUS_RELOAD_HISTORY_SIZE`（default 20）— reload 履歴保持件数
