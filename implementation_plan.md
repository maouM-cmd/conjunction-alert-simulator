# implementation_plan — CAS

## Phase 10V — 次着手

商用運用ロードマップ [requirements-commercial-ops.md](docs/requirements-commercial-ops.md) Phase 10+（Redis 共有 breach 状態、silence 削除 API 等）。

## Phase 10U — 完了

triage 自動 silence + Celery 定期 AM breach push。v1.28.0 ship 済み。

## Phase 10T — 完了

STM `open` 巻き戻し（opt-in）+ Alertmanager silences API。v1.27.0 ship 済み。

## Phase 10S — 完了

risk_level 別 per-fleet メトリクス + Alertmanager breach push、high-risk rule 雛形、Ops summary risk breakdown。v1.26.0 ship 済み。

## Phase 10R — 完了

6×6 アラート STM — `alert_stm_service` 正本化、`escalated` 状態、state-machine API、PD inbound / Pc auto-escalate 統合。v1.25.0 ship 済み。

## Phase 10Q — 完了

per-fleet Prometheus アラートメトリクス — 艦隊別 Gauge、open breach、alerting rule 雛形 API。v1.24.0 ship 済み。

## Phase 10P — 完了

PagerDuty 双方向 webhook — PD→CAS ack/resolve 同期、署名検証、ループ防止。v1.23.0 ship 済み。

## Phase 10O — 完了

PagerDuty acknowledge / resolve lifecycle — 安定 dedup_key、per-alert trigger、Ops 状態遷移連動。v1.22.0 ship 済み。

## Phase 10N — 完了

fleet 別 API SLO — 艦隊スコープ API 可用性計測、Ops fleet 表示、DB 永続化、Prometheus per-fleet。v1.21.0 ship 済み。

## Phase 10M — 完了

CDM σ TCA シフト — CDM encounter 共分散を CDM TCA 状態で評価、`cdm_encounter_tca_shift`。v1.20.0 ship 済み。

## Phase 10L — 完了

PagerDuty Events API v2 通知 — 全 alert 経路 + test ping + severity マッピング。v1.19.0 ship 済み。

## Phase 10K — 完了

TLE RTN 共分散 epoch→TCA 伝播、encounter Pc 統合、Ops propagated バッジ。v1.18.0 ship 済み。

## Phase 10J — 完了

API SLO DB 永続化 — 1h バケット write-through、日次履歴 API、Ops 7d トレンド、retention prune。v1.17.0 ship 済み。

## Phase 10I — 完了

Ops UI OIDC SSO — 管理者 + 艦隊メールマッピング、HttpOnly セッション、API Key 併用。v1.16.0 ship 済み。

## Phase 10H — 完了

API 99.9% SLO ダッシュボード — ローリング可用性、Prometheus Gauge、Ops API/UI 拡張。v1.15.0 ship 済み。

## Phase 10G — 完了

10F sweep 後の改善 best による `mitigation_planned` 自動遷移、optional auto-ack、`notify_mitigation_plan_auto`、Ops auto-planned バッジ。v1.14.0 ship 済み。

## Phase 10F — 完了

エスカレーション後の自動 COLA Δv スイープ、best 通知、mitigation `trigger_source`、Ops auto バッジ。v1.13.0 ship 済み。

## Phase 10E — 完了

スクリーニング自動 Pc 再計算、エスカレーション通知、`trigger_source`、Ops auto/ESCALATED バッジ。v1.12.0 ship 済み。

## Phase 10D — 完了

アラート Pc 再計算（CDM/TLE RTN）、`alert_pc_refinements`、Ops Pc 再計算 UI。v1.11.0 ship 済み。

## Phase 10C — 完了

COLA Δv スイープ、mitigation-plan 連携、Ops UI 拡張。v1.10.0 ship 済み。

## Phase 10B — 完了

SLA metrics（screening lag、HTTP counter、Ops SLA API/UI）。v1.9.0 ship 済み。

## Phase 10A — 完了

アラート連動 COLA preview（`alert_mitigation_previews`、Ops 回避試算 UI）。v1.8.0 ship 済み。

## Phase 9E — 完了

API Key 認証、監査ログ、`/health` DB/Redis/worker チェック。v1.7.0 ship 済み。

## Phase 9D — 完了

艦隊 10k + チャンク Celery、worker 水平スケール、Prometheus `/metrics`。v1.6.0 ship 済み。

## Phase 9C — 完了

`conjunction_alerts` 永続化、triage API、Ops UI タブ、新規 open のみ webhook。v1.5.0 ship 済み。

## Phase 9B — 完了

Celery + Redis 定期スクリーニング。v1.4.0 ship 済み。
