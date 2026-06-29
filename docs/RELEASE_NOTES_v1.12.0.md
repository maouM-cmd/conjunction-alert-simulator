# CAS v1.12.0 — Phase 10E Screening Auto Pc Refine & Escalation

**Conjunction Alert Simulator** v1.12.0 — スクリーニング連動の自動 Pc 再計算とエスカレーション通知。

## ハイライト

- **Phase 10E** — 高 Pc 新規 open アラートを Celery で自動 Pc 再計算
- `trigger_source`: `manual` / `screening_auto` を履歴に記録
- refined Pc が閾値超過時に **追加** エスカレーション通知
- Ops UI: `auto` バッジ + `ESCALATED` 表示
- 監査 `alert.pc_refine_auto` / `alert.pc_escalate`

## 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `AUTO_PC_REFINE_ENABLED` | `false` | 自動 Pc 再計算 |
| `AUTO_PC_REFINE_PC_MIN` | `1e-5` | enqueue 閾値 |
| `PC_ESCALATION_PC_MIN` | `1e-5` | エスカレーション閾値 |

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 10E 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase10e.md |

## 使い方

`AUTO_PC_REFINE_ENABLED=true` を worker/API に設定 → スクリーニングで高 Pc の新規 open が自動 refine → 閾値超過時にエスカレーション通知。Ops タブでは auto / ESCALATED バッジを確認。

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [v1.11.0 — Phase 10D Pc Refinement](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.11.0)

**License:** MIT
