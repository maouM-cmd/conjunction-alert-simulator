# CAS Phase 10U — 要件定義書

**版:** 10U  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10u.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第二十一フェーズ。10T で先送りした triage 自動 silence と Celery 定期 Alertmanager breach push を実装する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `fleet_metrics_sync_service`, `alertmanager_silence_service` 拡張 |
| Celery | `alertmanager_tasks.sync_fleet_alert_breaches` |
| env | `ALERTMANAGER_PUSH_CELERY_*`, `ALERTMANAGER_AUTO_SILENCE_*` |

---

## 2. 機能要件

### FR-10U-1: Celery 定期 breach push

- beat で fleet metrics 収集 + `sync_breaches`
- `ALERTMANAGER_PUSH_CELERY_ENABLED=true` 時は `/metrics` scrape から push を除外

### FR-10U-2: triage 自動 silence

- `acknowledged` / `false_positive` 遷移時に fleet silence 作成（opt-in）
- 失敗しても alert 遷移は維持

---

## 3. 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `ALERTMANAGER_PUSH_CELERY_ENABLED` | `false` | opt-in |
| `ALERTMANAGER_PUSH_CELERY_INTERVAL_SEC` | `60` | beat 間隔 |
| `ALERTMANAGER_AUTO_SILENCE_ON_TRIAGE_ENABLED` | `false` | opt-in |
| `ALERTMANAGER_AUTO_SILENCE_HOURS` | `4` | 自動 silence 時間 |

---

## 4. スコープ外

- Redis 共有 breach 状態、silence 削除 API、triage 以外の自動 silence

---

## 5. 成功条件

1. Celery で Prometheus 非依存の breach push
2. triage 完了時の opt-in 自動 silence
3. pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 10T](requirements-phase10t.md)
- [Phase 10S](requirements-phase10s.md)
