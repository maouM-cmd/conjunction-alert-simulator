# implementation_plan — CAS

## Phase 9B — Scheduled Screening Jobs（次着手）

商用運用ロードマップ [requirements-commercial-ops.md](docs/requirements-commercial-ops.md) の第二フェーズ。`screening_schedules` + Redis worker で定期スクリーニング。9A で登録した艦隊 TLE を自動解析し `screening_runs` に履歴を残す。

## Phase 9A — 完了

PostgreSQL + SQLAlchemy + Alembic で Fleet / Satellite CRUD、TLE revision（2 世代）+ rollback。`docker-compose.yml` に postgres 追加。v1.3.0 ship 済み。

## Phase 6G-ext live — 完了

Qiita / Zenn 本番に v1.2.2 原稿反映済み（ユーザー手動貼り付け）。
