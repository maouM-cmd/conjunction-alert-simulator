# Release v1.49.0 — Phase 10AP

**日付:** 2026-06-28

## 概要

fleet summary offset 数値入力、reload 履歴 stale purge Celery beat、dry-run CSV errors 列。

## Added

- Ops fleet summary offset 入力 + 移動ボタン
- Celery `purge_stale_prometheus_reload_history` + beat スケジュール
- dry-run preview CSV `errors` 列 + エラー行出力

## env

- `PROMETHEUS_RELOAD_HISTORY_PURGE_INTERVAL_SECONDS`（default 86400）
