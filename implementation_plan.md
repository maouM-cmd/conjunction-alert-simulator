# implementation_plan — CAS

## Phase 9C — Alert Lifecycle & Ops Dashboard（次着手）

商用運用ロードマップ [requirements-commercial-ops.md](docs/requirements-commercial-ops.md) の第三フェーズ。`conjunction_alerts` 永続化、triage 状態遷移、Ops UI。9B の screening run 結果からアラートを生成・通知（新規 open のみ）。

## Phase 9B — 完了

Celery + Redis + Beat で定期スクリーニング。`screening_schedules` / `screening_runs` REST API。v1.4.0 ship 済み。

## Phase 9A — 完了

PostgreSQL Fleet / Satellite CRUD、TLE revision。v1.3.0 ship 済み。
