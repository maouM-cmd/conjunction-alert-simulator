# implementation_plan — CAS

## Phase 10F — 次着手

商用運用ロードマップ [requirements-commercial-ops.md](docs/requirements-commercial-ops.md) Phase 10+（SSO、COLA 自動試算、99.9% SLA 等）。

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
