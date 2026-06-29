# Release v1.26.0 — Phase 10S

**日付:** 2026-06-28

## 概要

10Q で先送りした risk_level 別 per-fleet Prometheus メトリクスと Alertmanager 自動 push を実装。

## 変更

- `cas_fleet_alerts_by_risk_total{fleet_id,risk_level,status}` — high/medium/low × 6 状態
- `cas_fleet_high_risk_open_breach{fleet_id}` — open high ≥ `FLEET_ALERT_HIGH_RISK_THRESHOLD`
- rule 雛形に `CASFleetHighRiskOpenAlerts` 追加
- `ALERTMANAGER_PUSH_ENABLED=true` 時、open / high-risk breach の状態変化で AM へ push
- `POST /api/v1/ops/prometheus/alertmanager/test` — 接続テスト
- Ops fleet summary に open risk breakdown 表示

## テスト

275 passed（+7）

## 関連

- [requirements-phase10s.md](requirements-phase10s.md)
