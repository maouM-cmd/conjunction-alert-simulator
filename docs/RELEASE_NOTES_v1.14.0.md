# CAS v1.14.0 — Phase 10G Auto Mitigation Plan Transition

**Conjunction Alert Simulator** v1.14.0 — 自動 COLA スイープ後の改善 best による `mitigation_planned` 自動遷移。

## ハイライト

- **Phase 10G** — 10F sweep 完了後、改善 best preview があるアラートを条件付きで `mitigation_planned` へ自動遷移
- optional `AUTO_ACK_BEFORE_MITIGATION_PLAN` で `open→acknowledged` 先行
- `notify_mitigation_plan_auto` — 自動対策計画遷移の追加通知
- Ops UI: **auto-planned** バッジ（`auto_mitigation_planned`）
- 監査 `alert.mitigation_plan_auto`

## 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `AUTO_MITIGATION_PLAN_ENABLED` | `false` | 自動対策計画遷移 |
| `AUTO_ACK_BEFORE_MITIGATION_PLAN` | `false` | plan 前に open→ack |

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 10G 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase10g.md |

## 使い方

10F チェーン（`AUTO_PC_REFINE_ENABLED` + `AUTO_MITIGATION_SWEEP_ENABLED`）に加え worker で `AUTO_MITIGATION_PLAN_ENABLED=true` を設定。改善 best 取得後、Ops 介入なしで `mitigation_planned` へ遷移。open アラートは `AUTO_ACK_BEFORE_MITIGATION_PLAN=true` で auto-ack 後に plan。

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [v1.13.0 — Phase 10F Auto COLA Sweep](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.13.0)

**License:** MIT
