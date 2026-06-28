# CAS Phase 9B — 要件定義書

**版:** 9B  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase9b.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 9 第二フェーズ。9A で登録した艦隊 TLE を **Celery + Redis + Beat** で定期スクリーニングし、`screening_runs` に履歴を残す。9C（アラート triage）の前提。

| 変更箇所 | 内容 |
|---------|------|
| 新規 DB | `screening_schedules`, `screening_runs` |
| 新規 API | `/api/v1/screening/schedules`, `/runs` |
| Worker | Celery worker + Beat（60s poll） |
| [`docker-compose.yml`](../docker-compose.yml) | `redis`, `worker`, `beat` サービス |

---

## 2. 機能要件

### FR-P9B-1: Screening Schedules

- cron 式（5 フィールド）、fleet_id、解析パラメータ（threshold, duration, Pc 設定）
- `notify_on_complete` — Run 完了時 webhook
- CRUD + 論理削除

### FR-P9B-2: Celery Jobs

- Redis broker、`run_screening_job(run_id)` タスク
- Beat: 60 秒周期 `poll_due_schedules` → due schedule ごとに enqueue

### FR-P9B-3: Screening Runs

- status: `pending` / `running` / `completed` / `failed` / `dead_letter`
- started_at, finished_at, satellite_count, event_count, degraded, computation_time_ms

### FR-P9B-4: リトライ・通知

- Celery autoretry max 3 → `dead_letter`
- 完了時 [`webhook_notifier.notify_batch_fleet_events`](../backend/app/services/webhook_notifier.py) 再利用

### FR-P9B-5: 互換

- `DATABASE_URL` または `REDIS_URL` 未設定: screening API **503**
- 艦隊 > 25 衛星: 先頭 25 で実行、`degraded=true`（9D でチャンク）

---

## 3. スコープ外（9B）

- アラート永続・triage（9C）
- 1,000+ チャンク worker（9D）
- `/health` Redis チェック（9E）

---

## 4. 成功条件

1. Schedule CRUD + 手動 Run が REST で動作
2. Celery eager テストで Run が `completed` になる
3. 既存 pytest regression なし
4. docker compose で worker + beat 起動

---

## 5. 関連ドキュメント

- [Phase 9A](requirements-phase9a.md)
- [商用運用ロードマップ](requirements-commercial-ops.md)
