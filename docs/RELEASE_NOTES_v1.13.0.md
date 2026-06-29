# CAS v1.13.0 — Phase 10F Screening Auto COLA Sweep

**Conjunction Alert Simulator** v1.13.0 — エスカレーション後の自動 COLA Δv スイープと best 通知。

## ハイライト

- **Phase 10F** — 10E チェーン後に Δv スイープを Celery 自動実行
- `trigger_source`: `manual` / `screening_auto` を mitigation preview に記録
- best preview あり時に **追加** `notify_mitigation_best`
- Ops UI: mitigation 結果に `auto` バッジ
- 監査 `alert.mitigation_sweep_auto`

## 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `AUTO_MITIGATION_SWEEP_ENABLED` | `false` | 自動 Δv スイープ |
| `AUTO_MITIGATION_SWEEP_ON_ESCALATION_ONLY` | `true` | エスカレーション済みのみ |
| `AUTO_MITIGATION_SWEEP_PC_MIN` | `1e-5` | 非 escalation-only 時の Pc 閾値 |

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 10F 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase10f.md |

## 使い方

`AUTO_PC_REFINE_ENABLED=true` + `AUTO_MITIGATION_SWEEP_ENABLED=true` を worker に設定 → 高 Pc new open → auto Pc refine → escalation → auto COLA sweep → best 通知。Ops タブで mitigation `auto` バッジを確認。

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [v1.12.0 — Phase 10E Auto Pc Refine](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.12.0)

**License:** MIT
