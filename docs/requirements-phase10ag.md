# CAS Phase 10AG — 要件定義書

**版:** 10AG  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10ag.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第三十三フェーズ。10AF でスコープ外とした艦隊別 retention、ルール apply、履歴 alertname 複数フィルタを実装する。

| 変更箇所 | 内容 |
|---------|------|
| DB | `fleets.breach_history_retention_days` |
| Service | `effective_retention_days`、per-fleet purge、`apply_fleet_alert_rules` |
| API | PATCH breach-history-settings、POST fleet-alert-rules/apply、`alertnames` フィルタ |
| UI | retention 設定、alertname 複数選択、ルール apply |

---

## 2. 機能要件

### FR-10AG-1: 艦隊別 retention 日数

- `fleets.breach_history_retention_days`（nullable、1〜3650）
- `effective_retention_days` — override なし時は `ALERTMANAGER_BREACH_HISTORY_RETENTION_DAYS`
- `purge_old_breach_history` — 艦隊ごとの cutoff

### FR-10AG-2: PATCH breach-history-settings

- `PATCH /ops/fleets/{fleet_id}/breach-history-settings` — 管理者のみ
- `retention_days: null` — グローバル default に戻す

### FR-10AG-3: ルール apply

- `POST /ops/prometheus/fleet-alert-rules/apply` — 管理者のみ
- `PROMETHEUS_FLEET_RULES_OUTPUT_PATH` 設定時に atomic ファイル書き込み

### FR-10AG-4: 履歴 alertname 複数フィルタ

- `GET history?alertnames=` 繰り返しクエリ（OR フィルタ）
- 既存単一 `alertname` 後方互換

### FR-10AG-5: Ops UI

- breach 履歴 — alertname チェックボックス、retention 保存（管理者）
- fleet-alert-rules — 「ルールを適用」ボタン（管理者）

---

## 3. スコープ外

- Prometheus `/-/reload` webhook
- retention 横断 bulk 設定
- 履歴日付 range フィルタ

---

## 4. 成功条件

1. 艦隊別 retention が purge に反映される
2. PATCH settings / POST apply / alertnames フィルタが動作
3. Ops UI 反映
4. pytest 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 10AF](requirements-phase10af.md)
