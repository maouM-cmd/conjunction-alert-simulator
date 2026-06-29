# CAS Phase 10E — 要件定義書

**版:** 10E  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10e.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第五フェーズ。スクリーニングで新規 open された高リスクアラートに対し Celery で Pc 再計算を自動実行し、閾値超過時はエスカレーション通知を送る。

| 変更箇所 | 内容 |
|---------|------|
| DB | `alert_pc_refinements.trigger_source` |
| Worker | `refine_alert_pc_task` |
| 通知 | `notify_pc_escalation` |
| UI | auto / ESCALATED バッジ |

---

## 2. 機能要件

### FR-10E-1: 自動 Pc 再計算

- 新規 open アラートを条件付きで Celery enqueue（`AUTO_PC_REFINE_ENABLED`）

### FR-10E-2: trigger_source

- `manual` / `screening_auto` を `alert_pc_refinements` に記録

### FR-10E-3: エスカレーション通知

- `pc_refined >= PC_ESCALATION_PC_MIN` で Webhook/Slack/SMTP 追加通知

### FR-10E-4: 既存通知維持

- screening new-open 通知は変更なし。エスカレーションは追加

### FR-10E-5: Ops UI

- auto-refined バッジ + ESCALATED 表示

### FR-10E-6: 監査

- `alert.pc_refine_auto` / `alert.pc_escalate`

---

## 3. 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `AUTO_PC_REFINE_ENABLED` | `false` | 自動 Pc 再計算 |
| `AUTO_PC_REFINE_PC_MIN` | `1e-5` | enqueue 閾値（screening Pc） |
| `PC_ESCALATION_PC_MIN` | `1e-5` | エスカレーション閾値（refined Pc） |

---

## 4. スコープ外

- COLA 自動実行、SSO、API 99.9% SLA、screening 通知の refine 完了待ち

---

## 5. 成功条件

1. 高 Pc new open → auto refine → escalation（閾値超過時）
2. pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 10D](requirements-phase10d.md)
- [Phase 10A](requirements-phase10a.md)
