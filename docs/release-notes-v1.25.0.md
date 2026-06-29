# Release v1.25.0 — Phase 10R

**日付:** 2026-06-28

## 概要

6 状態アラート STM（State Transition Matrix）を `alert_stm_service` に集約し、第 6 状態 `escalated` を永続化。Ops API / UI / PagerDuty inbound / Pc 自動エスカレーションを統合。

## 変更

- 6 状態: `open`, `escalated`, `acknowledged`, `mitigation_planned`, `closed`, `false_positive`
- `GET /api/v1/ops/alerts/state-machine` — statuses / allowed_transitions / 6×6 matrix
- `ConjunctionAlertOut.allowed_next_statuses` — 個別 alert 返却時に許可遷移を付与
- Ops UI — ハードコード遷移表を廃止、`allowed_next_statuses` からボタン生成
- PagerDuty inbound — `escalated` からの ack → `acknowledged`、resolve 連鎖対応
- `ALERT_STM_AUTO_ESCALATE_STATUS=true` 時、Pc refine エスカレーションで `status=escalated`（default OFF、後方互換）
- fleet summary / Prometheus metrics に `escalated` 件数

## テスト

268 passed（+7 STM テスト）

## 関連

- [requirements-phase10r.md](requirements-phase10r.md)
