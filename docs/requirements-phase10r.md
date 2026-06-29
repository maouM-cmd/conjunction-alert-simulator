# CAS Phase 10R — 要件定義書

**版:** 10R  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10r.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第十八フェーズ。6 状態アラート STM（State Transition Matrix）を単一モジュールに集約し、第 6 状態 `escalated` を追加する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `alert_stm_service` |
| API | `GET /ops/alerts/state-machine` |
| UI | `allowed_next_statuses` 駆動ボタン |
| env | `ALERT_STM_AUTO_ESCALATE_STATUS` |

---

## 2. 機能要件

### FR-10R-1: 6 状態 STM 正本

- `open`, `escalated`, `acknowledged`, `mitigation_planned`, `closed`, `false_positive`
- 6×6 遷移マトリクス API 公開

### FR-10R-2: 統合

- `alert_service`, PagerDuty inbound, fleet metrics が STM を参照

### FR-10R-3: Pc 自動エスカレーション（opt-in）

- `ALERT_STM_AUTO_ESCALATE_STATUS=true` 時、Pc refine 後 `open` → `escalated`

### FR-10R-4: Ops UI

- `ConjunctionAlertOut.allowed_next_statuses` から遷移ボタン生成

---

## 3. 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `ALERT_STM_AUTO_ESCALATE_STATUS` | `false` | opt-in |

---

## 4. スコープ外

- risk_level 別メトリクス、Alertmanager push、`open` への巻き戻し

---

## 5. 成功条件

1. STM 正本が API / inbound / service で一貫
2. `escalated` が triage / metrics で利用可能
3. pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 10Q](requirements-phase10q.md)
- [Phase 10P](requirements-phase10p.md)
