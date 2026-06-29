# CAS v1.18.0 — Phase 10K Covariance Propagation

**Conjunction Alert Simulator** v1.18.0 — TLE RTN 共分散を epoch から TCA まで軸別時間成長で伝播し、encounter Pc 精度を向上。

## ハイライト

- **Phase 10K** — `propagate_rtn_variance`（R/T/N 軸別 km/day 成長）
- screening / Pc 再計算 / `/conjunctions` advanced+anisotropic に統合
- `covariance_source: tle_rtn_propagated`
- Ops UI: propagated σ バッジ
- デフォルト OFF（既存互換）

## 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `COV_PROPAGATION_ENABLED` | `false` | 伝播 ON |
| `COV_PROP_R_GROWTH_PER_DAY` | `0.10` | R 軸 km/day |
| `COV_PROP_T_GROWTH_PER_DAY` | `0.05` | T 軸 |
| `COV_PROP_N_GROWTH_PER_DAY` | `0.05` | N 軸 |

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 10K 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase10k.md |

## 使い方

`COV_PROPAGATION_ENABLED=true` + 既存 `use_anisotropic_cov` / advanced Pc で、古い TLE の encounter Pc が epoch→TCA 成長モデルを反映。Ops Pc 再計算結果に `propagated σ` バッジ表示。

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [v1.17.0 — Phase 10J SLO DB](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.17.0)

**License:** MIT
