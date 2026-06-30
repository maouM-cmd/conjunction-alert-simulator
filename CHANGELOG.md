# Changelog

All notable changes to Conjunction Alert Simulator (CAS) are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.48.0] - 2026-06-28

Phase 10AO — fleet summary offset UI + reload stale purge + dry-run CSV filter。

### Added

- **Phase 10AO:** fleet summary 前へ/次へ UI + `offset` API/CSV 連携
- reload 履歴 Redis stale エントリ物理 purge（push/read 時）
- `POST import?dry_run=true&changes_only=true` — dry-run preview 変更行のみ

## [1.47.0] - 2026-06-28

Phase 10AN — reload history TTL + dry-run preview CSV + fleet summary paging。

### Added

- **Phase 10AN:** reload 履歴 Redis TTL（`PROMETHEUS_RELOAD_HISTORY_REDIS_TTL_SECONDS`）
- `POST import?dry_run=true&format=csv` — dry-run preview CSV
- `GET summary?group_by=fleet&limit=&offset=` + Ops 表示件数

## [1.46.0] - 2026-06-28

Phase 10AM — reload history Redis + dry-run collapse + fleet name filter。

### Added

- **Phase 10AM:** reload 履歴 Redis 永続化（`cas:prometheus:reload:history`）
- `preview[].will_change` + Ops dry-run 変更行のみ折りたたみ
- `fleet_name_contains` クエリ + Ops 艦隊名フィルタ
- `PROMETHEUS_RELOAD_HISTORY_REDIS_ENABLED` env

## [1.45.0] - 2026-06-28

Phase 10AL — fleet summary CSV UI + dry-run preview table + reload history。

### Added

- **Phase 10AL:** `GET /prometheus/reload/history` — 直近 reload 履歴
- Ops UI — fleet summary CSV ボタン、dry-run preview テーブル、reload 履歴テーブル
- `PROMETHEUS_RELOAD_HISTORY_SIZE` env（default 20）

## [1.44.0] - 2026-06-28

Phase 10AK — per-fleet summary + import dry-run + reload 手動 UI。

### Added

- **Phase 10AK:** `GET history/summary?group_by=fleet` — 管理者日次×艦隊集計
- `POST import?dry_run=true` — retention CSV preview
- Ops UI — per-fleet summary テーブル、dry-run、Prometheus reload ボタン

## [1.43.0] - 2026-06-28

Phase 10AJ — summary CSV + retention import + reload polling。

### Added

- **Phase 10AJ:** `GET history/summary?format=csv`
- `POST /ops/fleets/breach-history-settings/import` — retention CSV インポート
- `reload_task_id` + `GET /ops/prometheus/reload/tasks/{task_id}`
- Ops UI — summary CSV、retention インポート、reload ポーリング

## [1.42.0] - 2026-06-28

Phase 10AI — reload リトライ/Celery fallback + retention CSV + 履歴日次集計。

### Added

- **Phase 10AI:** `reload_prometheus` リトライ（`PROMETHEUS_RELOAD_MAX_RETRIES`）
- Celery `prometheus_reload` タスク + `PROMETHEUS_RELOAD_CELERY_FALLBACK`
- `POST /ops/prometheus/reload` — 手動 reload（管理者）
- `GET breach-history-settings?format=csv` — retention CSV
- `GET history/summary` — 日次集計 API
- Ops UI — reload queued、retention CSV、日次 summary テーブル

## [1.41.0] - 2026-06-28

Phase 10AH — Prometheus reload + retention bulk + 履歴日付 range。

### Added

- **Phase 10AH:** apply 後 `PROMETHEUS_RELOAD_URL` reload webhook
- `GET /ops/fleets/breach-history-settings` — retention 一覧（管理者）
- `PATCH /ops/fleets/breach-history-settings/bulk` — 一括 retention 更新
- `GET history?since=&until=` — 日付 range フィルタ
- Ops UI — retention 一覧/bulk、since/until、reload ステータス

## [1.40.0] - 2026-06-28

Phase 10AG — 艦隊別 retention + ルール apply + alertnames フィルタ。

### Added

- **Phase 10AG:** `fleets.breach_history_retention_days` — 艦隊別 breach 履歴 retention
- `effective_retention_days` — per-fleet purge cutoff
- `PATCH /ops/fleets/{fleet_id}/breach-history-settings` — 管理者 retention 設定
- `POST /ops/prometheus/fleet-alert-rules/apply` — `PROMETHEUS_FLEET_RULES_OUTPUT_PATH` へ atomic 書き込み
- `GET history?alertnames=` — 複数 alertname OR フィルタ
- Ops UI — retention 保存、alertname チェックボックス、ルール apply

## [1.39.0] - 2026-06-28

Phase 10AF — per-fleet 履歴 purge + breaching 艦隊 rules + Ops UI。

### Added

- **Phase 10AF:** `purge_old_breach_history(fleet_id)` — 艦隊スコープ retention purge
- `DELETE /ops/prometheus/alertmanager/breach-states/history` — 手動 purge API
- Celery purge — active 艦隊ループ、`by_fleet` 集計
- `GET fleet-alert-rules?breaching_fleets_only=true` — breaching 艦隊のみ rule 出力
- `fleet_has_breaching_alert` — breach_state_store ヘルパー
- Ops UI — Prometheus アラートルール雛形ダウンロード

## [1.38.0] - 2026-06-28

Phase 10AE — breach gauge ルール + 履歴フィルタ。

### Added

- **Phase 10AE:** `GET fleet-alert-rules?breaching_only=true` — breach Gauge ベース expr
- `render_fleet_alert_rules(breaching_only)` — `cas_fleet_*_breach == 1` ルール
- `GET history` — `source` / `breaching_only` クエリ（単艦隊 + 管理者横断）
- Ops UI — 履歴 source セレクト + breaching のみチェックボックス

## [1.37.0] - 2026-06-28

Phase 10AD — 管理者横断 breach 履歴 + retention purge。

### Added

- **Phase 10AD:** `GET breach-states/history` — `fleet_id` 省略で管理者横断一覧
- `FleetBreachHistoryMultiListOut` / `FleetBreachHistoryEntryOut` — fleet_name 付き履歴
- `list_all_history` / `purge_old_breach_history` — retention purge（default 90 日）
- `ALERTMANAGER_BREACH_HISTORY_RETENTION_DAYS` — 履歴保持日数
- Celery `purge_old_breach_history` — 日次 beat タスク
- Ops UI — 全艦隊 breach 履歴テーブル + CSV ダウンロード

## [1.36.0] - 2026-06-28

Phase 10AC — breaching-only フィルタ + breach 変更履歴。

### Added

- **Phase 10AC:** `fleet_alert_breach_history` — breach 状態遷移の時系列記録
- `ALERTMANAGER_BREACH_HISTORY_ENABLED` — opt-in 履歴記録
- `GET breach-states?breaching_only=true` — breaching 行のみフィルタ
- `GET /ops/prometheus/alertmanager/breach-states/history` — JSON / CSV export
- `breach_history_service` — `sync` / `manual` / `sticky_clear` 記録
- Alembic `013_fleet_alert_breach_history`
- Ops UI — breaching のみチェックボックス、履歴テーブル、CSV ダウンロード

## [1.35.0] - 2026-06-28

Phase 10AB — breach sticky 上書き。

### Added

- **Phase 10AB:** `is_manual_sticky` — 手動 breach 状態を `sync_breaches` から保護
- `ALERTMANAGER_BREACH_STATE_STICKY_OVERRIDE_ENABLED` — opt-in sticky モード
- `DELETE /ops/prometheus/alertmanager/breach-states/sticky` — sticky 解除 + 監査
- `PUT` breach-states に `sticky` フラグ（default true）
- Alembic `012_fleet_alert_breach_states`
- Ops UI — sticky バッジ、「自動同期」ボタン

## [1.34.0] - 2026-06-28

Phase 10AA — breach 横断一覧 + 手動上書き。

### Added

- **Phase 10AA:** `list_all_fleet_breach_states` — active 艦隊横断 breach 状態
- `GET /ops/prometheus/alertmanager/breach-states` — `fleet_id` 省略時は管理者横断一覧
- `PUT /ops/prometheus/alertmanager/breach-states` — opt-in 手動上書き + 監査 `alert.breach_state_manual_override`
- `ALERTMANAGER_BREACH_STATE_MANUAL_OVERRIDE_ENABLED` — 手動上書き gate
- Ops UI — 全艦隊 breach テーブル（管理者）、breaching/ok 上書きボタン

## [1.33.0] - 2026-06-28

Phase 10Z — DB dual push 拡張 + breach 状態 Ops UI。

### Added

- **Phase 10Z:** `shared_breach_state_enabled` — Redis または DB 共有時に metrics dual push
- `should_sync_breaches_on_metrics_scrape()` — Celery ON + DB ON でも `/metrics` から breach push
- `list_fleet_breach_states` / `breach_state_backend` — 艦隊 breach 状態参照
- `GET /ops/prometheus/alertmanager/breach-states` — fleet スコープ breach 状態 API
- Ops UI — Alertmanager Breach 状態テーブル（breaching / ok 表示）

## [1.32.0] - 2026-06-28

Phase 10Y — silence 選択 bulk 削除。

### Added

- **Phase 10Y:** `delete_silences_by_ids` — 指定 silence ID 群の一括削除
- `POST /ops/prometheus/alertmanager/silences/bulk-delete` — fleet スコープ認可付き
- `AlertmanagerSilenceBulkDelete` スキーマ
- Ops UI — チェックボックス選択・全選択・「選択した silence を削除」

## [1.31.0] - 2026-06-28

Phase 10X — breach DB 永続化 + Redis 時 dual push。

### Added

- **Phase 10X:** `fleet_alert_breach_states` テーブル — breach 状態 DB 永続化（opt-in）
- `ALERTMANAGER_PUSH_DB_STATE_ENABLED` — store 優先順位 Redis > DB > in-memory
- `should_sync_breaches_on_metrics_scrape()` — Celery ON + Redis ON 時に `/metrics` からも breach push

## [1.30.0] - 2026-06-28

Phase 10W — silence 一括削除 + Ops UI silence 管理。

### Added

- **Phase 10W:** `delete_silences_for_fleet` — fleet 単位（+ optional alertname）active silence 一括削除
- `DELETE /ops/prometheus/alertmanager/silences?fleet_id=` — bulk 削除 API
- `AlertmanagerSilenceBulkDeletedOut` スキーマ
- Ops UI — silence 一覧・作成・単体削除・艦隊一括削除

## [1.29.0] - 2026-06-28

Phase 10V — Redis 共有 breach 状態 + Alertmanager silence 削除 API。

### Added

- **Phase 10V:** `breach_state_store` — Redis `cas:am:breach:{fleet_id}:{alertname}` でワーカー間 breach 状態共有
- `ALERTMANAGER_PUSH_REDIS_STATE_ENABLED`（default false）— opt-in、Redis 不可時は in-memory フォールバック
- `alertmanager_silence_service.get_silence` / `delete_silence` — `DELETE /api/v2/silence/{id}` 連携
- `DELETE /ops/prometheus/alertmanager/silences/{silence_id}` — fleet スコープ認可付き削除 API
- `AlertmanagerSilenceDeletedOut` スキーマ

## [1.28.0] - 2026-06-28

Phase 10U — triage 自動 silence + Celery 定期 AM push。

### Added

- **Phase 10U:** `fleet_metrics_sync_service` — fleet Gauge 収集の共通化
- Celery beat `sync_fleet_alert_breaches` — Prometheus 非依存の breach push
- `ALERTMANAGER_AUTO_SILENCE_ON_TRIAGE_ENABLED` — ack/false_positive 時に fleet silence 自動作成
- env: `ALERTMANAGER_PUSH_CELERY_ENABLED`, `ALERTMANAGER_PUSH_CELERY_INTERVAL_SEC`, `ALERTMANAGER_AUTO_SILENCE_HOURS`
- 監査 `alert.alertmanager_auto_silence`

## [1.27.0] - 2026-06-28

Phase 10T — STM `open` 巻き戻し + Alertmanager silences。

### Added

- **Phase 10T:** `ALERT_STM_REOPEN_TO_OPEN_ENABLED` — `acknowledged` / `escalated` / `false_positive` → `open`（opt-in）
- `alert_stm_service.effective_allowed_transitions()` — reopen 統合
- `alertmanager_silence_service` — `POST/GET /api/v2/silences` 連携
- `POST /ops/prometheus/alertmanager/silences`, `GET` 一覧 API
- `AlertStateMachineOut.reopen_to_open_enabled`
- env: `ALERTMANAGER_SILENCES_ENABLED`, `ALERTMANAGER_SILENCE_DEFAULT_HOURS`

## [1.26.0] - 2026-06-28

Phase 10S — risk_level 別メトリクス + Alertmanager push。

### Added

- **Phase 10S:** `cas_fleet_alerts_by_risk_total{fleet_id,risk_level,status}`, `cas_fleet_high_risk_open_breach`
- `alertmanager_push_service` — breach 状態変化時に `POST /api/v2/alerts`
- `CASFleetHighRiskOpenAlerts` rule 雛形、`POST /ops/prometheus/alertmanager/test`
- `FleetOpsSummaryOut.open_high_count` / `open_medium_count` / `open_low_count`
- env: `FLEET_ALERT_HIGH_RISK_THRESHOLD`, `ALERTMANAGER_PUSH_ENABLED`, `ALERTMANAGER_URL`

## [1.25.0] - 2026-06-28

Phase 10R — 6×6 アラート STM（State Transition Matrix）。

### Added

- **Phase 10R:** 6 状態 STM 正本化 — `alert_stm_service`（`escalated` 追加）
- `GET /api/v1/ops/alerts/state-machine` — 6×6 遷移マトリクス API
- `ConjunctionAlertOut.allowed_next_statuses` — Ops UI ボタン生成
- `FleetOpsSummaryOut.escalated_count`、fleet metrics に `escalated`
- PagerDuty inbound — `escalated` 状態の ack/resolve 連鎖
- env: `ALERT_STM_AUTO_ESCALATE_STATUS`（default false）— Pc refine 後 `open` → `escalated`

## [1.24.0] - 2026-06-28

Phase 10Q — per-fleet Prometheus アラートメトリクス。

### Added

- **Phase 10Q:** 艦隊別アラート件数 Prometheus export
- `cas_fleet_alerts_total{fleet_id,status}`, `cas_fleet_open_alerts_breach{fleet_id}`
- `GET /ops/prometheus/fleet-alert-rules` — alerting rule 雛形（yaml/json）
- `fleet_alert_metrics_service`
- env: `FLEET_ALERT_METRICS_ENABLED`（default false）、`FLEET_ALERT_OPEN_THRESHOLD`（default 10）

## [1.23.0] - 2026-06-28

Phase 10P — PagerDuty 双方向 webhook（PD→CAS）。

### Added

- **Phase 10P:** `POST /api/v1/integrations/pagerduty/webhook` — PD incident ack/resolve → CAS 状態同期
- `pagerduty_inbound_service` — 署名検証、`cas-alert-{id}` 逆引き、冪等処理
- `transition_alert(..., skip_pagerduty_outbound)` — inbound ループ防止
- 監査 `alert.pagerduty_inbound`
- env: `PAGERDUTY_INBOUND_SYNC_ENABLED`（default false）、`PAGERDUTY_WEBHOOK_SIGNING_SECRET`

## [1.22.0] - 2026-06-28

Phase 10O — PagerDuty acknowledge / resolve lifecycle。

### Added

- **Phase 10O:** `PAGERDUTY_LIFECYCLE_ENABLED` — PagerDuty Events API v2 acknowledge / resolve
- 安定 `dedup_key=cas-alert-{alert_id}`（新規 trigger、escalation、mitigation 統一）
- `notify_new_alerts` per-alert trigger（lifecycle ON 時）
- `transition_alert` → `acknowledged` / `closed` / `false_positive` で PD lifecycle 連動
- env: `PAGERDUTY_LIFECYCLE_ENABLED`（default false）

## [1.21.0] - 2026-06-28

Phase 10N — fleet 別 API SLO。

### Added

- **Phase 10N:** fleet スコープ API Key / OIDC セッション単位の API 可用性計測
- `api_slo_fleet_context`, `fleet_api_availability_service`
- DB `api_slo_fleet_hourly_buckets` + write-through（10J 連携）
- `FleetSlaOut` fleet API フィールド、`GET /ops/sla/api-history?fleet_id=`
- Prometheus `cas_fleet_api_availability_ratio`, `cas_fleet_api_slo_ok`
- Ops UI fleet API SLO + 7d トレンド
- env: `SLA_FLEET_API_SLO_ENABLED`（default false）

## [1.20.0] - 2026-06-28

Phase 10M — CDM σ TCA シフト。

### Added

- **Phase 10M:** CDM encounter 共分散を CDM 記載 TCA の軌道状態で評価
- `cdm_tca_shift_service` — `index_nearest_tca`、`encounter_states_for_cdm`
- `covariance_source: cdm_encounter_tca_shift`（`/conjunctions`、CDM compare、Pc refinement 経路）
- env: `CDM_TCA_SHIFT_ENABLED`（default false）

## [1.19.0] - 2026-06-28

Phase 10L — PagerDuty 通知連携。

### Added

- **Phase 10L:** `ALERT_WEBHOOK_FORMAT=pagerduty` — PagerDuty Events API v2
- `PAGERDUTY_ROUTING_KEY` env（`ALERT_WEBHOOK_URL` 不要）
- 全通知経路対応: conjunction / batch / new alerts / Pc escalation / mitigation / test ping
- severity: escalation→critical, high→error, medium→warning, test→info
- `/health` `alert_delivery_format: pagerduty`

## [1.18.0] - 2026-06-28

Phase 10K — TLE RTN 共分散伝播強化。

### Added

- **Phase 10K:** TLE epoch から TCA まで RTN 軸別時間成長伝播
- `covariance_propagation_service` — `propagate_rtn_variance`、成長率 env
- `covariance_source: tle_rtn_propagated`（screening / Pc 再計算 / `/conjunctions`）
- Ops UI: propagated σ バッジ
- env: `COV_PROPAGATION_ENABLED`（default false）、`COV_PROP_*_GROWTH_PER_DAY`

## [1.17.0] - 2026-06-28

Phase 10J — API SLO DB 永続化。

### Added

- **Phase 10J:** 1h API SLO バケット PostgreSQL 永続化（`api_slo_hourly_buckets`）
- `slo_persistence_service` — write-through upsert、日次 rollup、retention prune、hydrate
- `GET /api/v1/ops/sla/api-history?days=30` — 日次 API 可用性履歴
- Ops UI: 7 日 API SLO トレンド行
- Alembic `010_api_slo_buckets`
- env: `SLA_API_PERSIST_ENABLED`（default false）, `SLA_API_RETENTION_DAYS`（default 90）

## [1.16.0] - 2026-06-28

Phase 10I — Ops UI OIDC SSO（Admin + Fleet）。

### Added

- **Phase 10I:** OIDC Authorization Code + PKCE、HttpOnly セッション cookie
- `GET /api/v1/auth/oidc/*`, `/auth/me`, `/auth/logout`
- 管理者 `OPS_OIDC_ADMIN_EMAILS` + 艦隊 `OPS_OIDC_FLEET_MAPPINGS`
- `AuthPrincipal` OIDC 拡張 — API Key 併用
- Ops UI: SSO ログイン / ログアウト / 認証状態表示
- 監査: `auth.oidc_login`
- 依存: `authlib`

## [1.15.0] - 2026-06-28

Phase 10H — API 99.9% SLO Dashboard。

### Added

- **Phase 10H:** ローリング窓 API 可用性 SLO（99.9% 目標）
- `api_availability_service` — 1h バケット、5xx ベース可用性
- Prometheus: `cas_api_availability_ratio`, `cas_api_slo_ok`
- `GET /api/v1/ops/sla` — API SLO フィールド拡張
- Ops UI: API availability OK/BREACH 表示
- env: `SLA_API_TARGET_PERCENT`, `SLA_API_ROLLING_WINDOW_HOURS`

## [1.14.0] - 2026-06-28

Phase 10G — Auto Mitigation Plan Transition。

### Added

- **Phase 10G:** 10F sweep 完了後、改善 best ありで条件付き `mitigation_planned` 自動遷移
- `maybe_auto_mitigation_plan` — optional `open→acknowledged`（`AUTO_ACK_BEFORE_MITIGATION_PLAN`）
- `notify_mitigation_plan_auto` — 自動対策計画遷移の追加通知
- `ConjunctionAlertOut.auto_mitigation_planned` + Ops UI auto-planned バッジ
- 監査: `alert.mitigation_plan_auto`
- env: `AUTO_MITIGATION_PLAN_ENABLED`, `AUTO_ACK_BEFORE_MITIGATION_PLAN`

## [1.13.0] - 2026-06-28

Phase 10F — Screening Auto COLA Sweep。

### Added

- **Phase 10F:** 10E エスカレーション後の自動 Δv スイープ（Celery）
- `alert_mitigation_previews.trigger_source` — `manual` / `screening_auto`（Alembic 009）
- `mitigation_sweep_task` — worker 非同期 COLA スイープ
- `notify_mitigation_best` — best preview 追加通知
- `MitigationPreviewOut.trigger_source` + Ops UI auto バッジ
- 監査: `alert.mitigation_sweep_auto`
- env: `AUTO_MITIGATION_SWEEP_ENABLED`, `AUTO_MITIGATION_SWEEP_ON_ESCALATION_ONLY`, `AUTO_MITIGATION_SWEEP_PC_MIN`

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
