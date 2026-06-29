# Release v1.29.0 — Phase 10V

**日付:** 2026-06-28

## 概要

Celery 複数ワーカー向け Redis 共有 breach 状態と Alertmanager silence 削除 API を実装。

## 変更

- `ALERTMANAGER_PUSH_REDIS_STATE_ENABLED=true` — Redis `cas:am:breach:{fleet_id}:{alertname}` で breach 状態をプロセス間共有（`REDIS_URL` 必須）
- default OFF 時は in-memory フォールバック（既存挙動維持）
- `DELETE /api/v1/ops/prometheus/alertmanager/silences/{silence_id}` — fleet スコープ認可付き silence 削除
- `breach_state_store` — `alertmanager_push_service.sync_breaches` が store 経由で状態変化時のみ push

## テスト

301 passed（+8、環境依存の scale_out 1 件除く）

## 関連

- [requirements-phase10v.md](requirements-phase10v.md)
