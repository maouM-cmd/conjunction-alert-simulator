# Release v1.24.0 — Phase 10Q

**日付:** 2026-06-28

## 概要

艦隊別 conjunction alert 件数を Prometheus に export し、Ops API で Prometheus alerting rule 雛形を自動生成する。

## 変更

- `FLEET_ALERT_METRICS_ENABLED=true` で per-fleet Gauge 有効
- `cas_fleet_alerts_total{fleet_id,status}` — 5 状態の件数
- `cas_fleet_open_alerts_breach{fleet_id}` — open 件数が閾値超過時 1
- `GET /api/v1/ops/prometheus/fleet-alert-rules` — yaml/json 形式の rule 雛形
- `FLEET_ALERT_OPEN_THRESHOLD`（default 10）

## テスト

261 passed

## 関連

- [requirements-phase10q.md](requirements-phase10q.md)
