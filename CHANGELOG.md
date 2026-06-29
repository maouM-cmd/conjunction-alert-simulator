# Changelog

All notable changes to Conjunction Alert Simulator (CAS) are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.12.0] - 2026-06-28

Phase 10E — Screening Auto Pc Refine & Escalation。

### Added

- **Phase 10E:** スクリーニング新規 open の自動 Pc 再計算（Celery、`AUTO_PC_REFINE_ENABLED`）
- `alert_pc_refinements.trigger_source` — `manual` / `screening_auto`（Alembic 008）
- `refine_alert_pc_task` — worker 非同期 Pc 再計算
- `notify_pc_escalation` — refined Pc 閾値超過時の追加通知
- `ConjunctionAlertOut.escalated` + Ops UI auto / ESCALATED バッジ
- 監査: `alert.pc_refine_auto` / `alert.pc_escalate`
- env: `AUTO_PC_REFINE_PC_MIN`, `PC_ESCALATION_PC_MIN`

## [1.11.0] - 2026-06-28

Phase 10D — Alert Pc Refinement。

### Added

- **Phase 10D:** 永続化アラートの Pc 再計算（CDM RTN 優先、TLE RTN フォールバック）
- `alert_pc_refinements` テーブル（Alembic 007）
- `POST /api/v1/ops/alerts/{id}/pc-refine` — 201
- `GET /api/v1/ops/alerts/{id}/pc-refinements` — 履歴
- `ConjunctionAlertOut.latest_pc_refinement` — screening vs refined 併記
- 監査: `alert.pc_refine`
- Ops UI: Pc 再計算ボタン + screening → refined 表示

## [1.10.0] - 2026-06-28

Phase 10C — COLA Sweep & Mitigation Planning。

### Added

- **Phase 10C:** Δv スイープ API + 対策計画連携
- `POST /api/v1/ops/alerts/{id}/mitigation-sweep` — best 選定（最小改善 Δv）
- `POST /api/v1/ops/alerts/{id}/mitigation-plan` — preview 付き `mitigation_planned` 遷移
- 監査: `alert.mitigation_sweep` / `alert.mitigation_plan`
- Ops UI: direction/Δv 入力、Δv スイープ、試算→対策計画ボタン

## [1.9.0] - 2026-06-28

Phase 10B — SLA Metrics（FR-9E-4 計測可能化）。

### Added

- **Phase 10B:** スクリーニング lag / overdue を Prometheus + Ops API で可視化
- `cas_screening_lag_seconds{fleet_id}` / `cas_screening_overdue_fleets` / `cas_http_requests_total`
- HTTP metrics middleware（`/metrics` 除外）
- `GET /api/v1/ops/sla` — 艦隊 SLA サマリ
- Ops UI: summary に Screening lag OK/OVERDUE
- env: `SLA_SCREENING_MAX_LAG_HOURS=24`

## [1.8.0] - 2026-06-28

Phase 10A — Alert-Linked COLA Preview（回避試算連携）。

### Added

- **Phase 10A:** 永続化アラートから maneuver preview を実行・DB 保存
- `alert_mitigation_previews` テーブル（Alembic 006）
- `POST /api/v1/ops/alerts/{id}/mitigation-preview` — 201
- `GET /api/v1/ops/alerts/{id}/mitigation-previews` — 履歴
- `ConjunctionAlertOut.latest_mitigation_preview` — 最新試算
- 監査: `alert.mitigation_preview`
- Ops UI: アラート行「回避試算」ボタン + 結果表示

## [1.7.0] - 2026-06-28

Phase 9E — Platform Baseline（認証・監査・readiness）。

### Added

- **Phase 9E:** fleet スコープ API Key（`X-API-Key`、`CAS_API_KEY_REQUIRED` デフォルト false）
- `api_keys` / `audit_logs` テーブル（Alembic 005）
- キー管理: `POST/GET/DELETE /api/v1/fleets/{id}/api-keys`
- 監査: alert 遷移、TLE 更新、schedule CRUD → `GET /api/v1/ops/audit`
- Beat タスク `purge_old_audit_logs`（`AUDIT_LOG_RETENTION_DAYS=90`）
- `/health` 拡張: `checks.postgres` / `checks.redis` / `checks.worker`、`status`: ok | degraded
- Ops UI: 任意 API Key 入力（localStorage）

### Changed

- fleet / screening / ops API は `CAS_API_KEY_REQUIRED=true` 時に保護
- ad-hoc 解析 API は公開維持（NFR-C-6）

## [1.6.0] - 2026-06-28

Phase 9D — Scale-Out（1,000+ 衛星）。

### Added

- **Phase 9D:** スクリーニング チャンク orchestration（50 sat/job、`parent_run_id` / Alembic 004）
- 艦隊上限 `FLEET_MAX_SATELLITES=10000`、超過時 409
- Celery `run_screening_chunk` タスク、worker `--concurrency` / `docker compose --scale worker=N`
- Space-Track CDM Redis 共有レートリミット（`spacetrack_rate_limiter`）
- **`GET /metrics`** — Prometheus（`cas_open_alerts_total`、`cas_screening_runs_total`、`cas_celery_queue_depth`、`cas_info`）
- env: `SCREENING_CHUNK_SIZE`、`SCREENING_MAX_WORKERS`、`CELERY_WORKER_CONCURRENCY`

### Changed

- 定期スクリーニング: 25 件 truncate + `degraded=true` を廃止しチャンク分割に置換
- ad-hoc `/api/v1/conjunctions/batch` の 25 上限は互換維持

## [1.5.0] - 2026-06-28

Phase 9C — Alert Lifecycle & Ops Dashboard。

### Added

- **Phase 9C:** `conjunction_alerts` 永続化（Alembic 003）、triage 状態遷移
- REST: `/api/v1/ops/alerts`、`/ops/fleets/{id}/summary`
- screening run から ingest、±24h 重複抑制、**新規 open のみ** webhook
- UI: **運用 Ops** タブ（艦隊サマリ、アラート一覧、Ack / 対策計画 / クローズ / 誤検知）

## [1.4.0] - 2026-06-28

Phase 9B — Scheduled Screening Jobs（Celery + Redis + Beat）。

### Added

- **Phase 9B:** `screening_schedules` / `screening_runs`（PostgreSQL + Alembic 002）
- REST: `/api/v1/screening/schedules` CRUD、手動 Run、`/runs` 一覧
- Celery worker + Beat（60s poll）で cron 定期スクリーニング
- 既存 `run_batch_conjunction_analysis` + `notify_batch_fleet_events` を worker から再利用
- `docker-compose.yml` に `redis` / `worker` / `beat` サービス
- 艦隊 > 25 衛星は先頭 25 で実行し `degraded=true`（9D でチャンク対応予定）

## [1.3.0] - 2026-06-28

Phase 9A — Fleet Registry & Persistence（商用運用ロードマップ第一フェーズ）。

### Added

- **Phase 9A:** PostgreSQL + SQLAlchemy + Alembic — `fleets` / `satellites` / `tle_revisions`
- REST: `/api/v1/fleets` CRUD、`/fleets/{id}/satellites`、TLE 更新 revision（2 世代）、`POST /satellites/{id}/rollback`
- `docker-compose.yml` に `postgres` サービス、起動時 `alembic upgrade head`
- `DATABASE_URL` 未設定時 fleet API は 503、既存 ad-hoc batch / conjunction は互換維持

## [1.2.2] - 2026-06-28

Phase 8B — SMTP メール通知。

### Added

- **Phase 8B:** `ALERT_WEBHOOK_FORMAT=smtp`、`SMTP_*` env、単一衛星 / batch / test ping 対応、`/health` `alert_delivery_format: smtp`

## [1.2.1] - 2026-06-28

Phase 8 — Space-Track CDM 自動マージ（単一衛星 + batch）。

### Added

- **Phase 8A:** `auto_spacetrack_cdm` on `/conjunctions`、`spacetrack_cdm_*` レスポンスメタ、UI チェックボックス
- **Phase 8A-ext:** batch `/conjunctions/batch` 同機能、`BatchSummaryOut` fleet CDM 集計

## [1.2.0] - 2026-06-28

Phase 7 機能拡張 — 高度プリフィルタ UX、Space-Track CDM RTN 共分散、Slack Bot 通知。

### Added

- **Phase 7C:** `use_altitude_prefilter` on `/conjunctions` and batch、`debris_candidates_count`、Live Demo cold start `/health` ポーリング / `apiPost` リトライ
- **Phase 7A:** Space-Track CDM RTN 共分散パース、`fetch_cdm_detail` lazy 取得、compare-alert `sigma_source: cdm_covariance`、`has_rtn_covariance` UI バッジ
- **Phase 7B:** `ALERT_WEBHOOK_FORMAT=slack_bot`（`SLACK_BOT_TOKEN` + `SLACK_CHANNEL_ID`）、`/health` `alert_delivery_*`

## [1.1.1] - 2026-06-28

Phase 6 ポートフォリオ完結 — Live Demo、Zenn 公開、Render CI/CD、仕上げドキュメント。

### Added

- **Phase 6A:** 公開チェックリスト、GitHub Release v1.1.0、Zenn 原稿・投稿手順
- **Phase 6C:** Render Live Demo URL、verify_deploy CLI、deploy-render-phase6c.md
- **Phase 6B:** GitHub Actions deploy.yml（pytest → Render Hook → verify_deploy）
- **Phase 6E:** Qiita 原稿、Social Preview 素材、CI pytest 一本化、v1.1.1 release notes

## [1.1.0] - 2026-06-28

Phase 5 リリース — クラウド manifest、運用 Webhook、CDM σ 一覧、デモ刷新。

### Added

- **Phase 5B:** 同一オリジン API、Render/Fly manifest、`docs/deploy-cloud.md`、動的 `PORT`
- **Phase 5C:** Slack Incoming Webhook（`ALERT_WEBHOOK_FORMAT=slack`）、`cdm_text` + `apply_cdm_covariance` on `/conjunctions`、batch Webhook + UI テスト
- **Phase 5D:** `find_demo_pair` Advanced Pc メタ、Phase 5 デモ PNG/GIF、Zenn 原稿更新

## [1.0.0] - 2026-06-28

Phase 4 完成リリース — 接近監視から Pc / CDM 運用連携 / Docker まで一気通貫。

### Added

- **Phase 1:** TLE 入力 → デブリ接近検出、CesiumJS 3D 可視化、回避マニューバ試算
- **Phase 2:** Foster 2D 衝突確率 Pc、Space-Track TLE 連携（CelesTrak フォールバック）
- **Phase 3:** CDM インポート・比較 UI、コンステレーション batch API（最大 25 衛星）
- **Phase 3.5:** CDM RTN 共分散 encounter 射影、batch ProcessPool 並列化
- **Phase 4A:** Alfriend encounter plane Pc、Monte Carlo（CDM 比較）
- **Phase 4A-Ext:** 一覧 `/conjunctions` に `use_advanced_pc` opt-in
- **Phase 4B:** Space-Track `cdm_public` 取得、CDM アラート UI、CDM KVN エクスポート
- **Phase 4B-Ext:** TLE RTN 非等方共分散、Webhook 通知スタブ
- **Phase 4C:** Dockerfile / docker-compose、デプロイ手順
- **Phase 4D:** デモ PNG/GIF、技術ブログ Phase 4 版、ポートフォリオ素材

### Changed

- 接近イベント一覧は Pc 降順ソート（Phase 2 以降）
- リスクレベルは Pc 優先判定（high ≥ 10⁻⁴、medium ≥ 10⁻⁶）

[1.2.2]: https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.2.2
[1.2.1]: https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.2.1
[1.2.0]: https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.2.0
[1.1.1]: https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.1.1
[1.1.0]: https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.1.0
[1.0.0]: https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.0.0
