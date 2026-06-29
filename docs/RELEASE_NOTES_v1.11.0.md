# CAS v1.11.0 — Phase 10D Alert Pc Refinement

**Conjunction Alert Simulator** v1.11.0 — 永続化アラートの Pc 再計算と screening vs refined 比較。

## ハイライト

- **Phase 10D** — CDM RTN 共分散優先、TLE RTN フォールバックで Pc 再計算
- `POST .../pc-refine` — 再計算結果を `alert_pc_refinements` に履歴保存
- `GET .../pc-refinements` — 履歴一覧
- Ops UI: **Pc 再計算** ボタン + screening → refined 表示
- 監査 `alert.pc_refine`

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 10D 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase10d.md |

## 使い方

Ops タブ → アラート行で **Pc 再計算** → Pc 列に screening 値と refined 値（方法付き）が表示されます。

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [v1.10.0 — Phase 10C COLA Sweep](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.10.0)

**License:** MIT
