# Release v1.27.0 — Phase 10T

**日付:** 2026-06-28

## 概要

STM `open` 巻き戻し（opt-in）と Alertmanager silences API を実装。

## 変更

- `ALERT_STM_REOPEN_TO_OPEN_ENABLED=true` 時、`acknowledged` / `escalated` / `false_positive` → `open`
- `GET /ops/alerts/state-machine` に `reopen_to_open_enabled` 追加
- `POST /api/v1/ops/prometheus/alertmanager/silences` — fleet silence 作成
- `GET /api/v1/ops/prometheus/alertmanager/silences` — active silences 一覧
- Ops UI — `open` 遷移ラベル「再オープン」

## テスト

287 passed（+12）

## 関連

- [requirements-phase10t.md](requirements-phase10t.md)
