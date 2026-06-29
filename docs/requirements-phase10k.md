# CAS Phase 10K — 要件定義書

**版:** 10K  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10k.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第十一フェーズ。TLE RTN 共分散を TLE epoch から TCA まで軸別時間成長で伝播し、encounter Pc 精度を向上する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `covariance_propagation_service` |
| 統合 | screening / Pc 再計算 / `/conjunctions` |
| UI | Ops propagated σ バッジ |

---

## 2. 機能要件

### FR-10K-1: epoch→TCA 伝播

- RTN 対角共分散の軸別成長: `var_axis(t) = (σ0_axis + k_axis * Δt_days)²`

### FR-10K-2: encounter 統合

- `COV_PROPAGATION_ENABLED=true` 時 `encounter_covariance_from_tle_pair` が伝播 RTN を使用

### FR-10K-3: 経路統合

- `analysis.py`、`pc_refinement_service.py`、`/conjunctions` advanced+anisotropic

### FR-10K-4: covariance_source

- `tle_rtn_propagated` を API / refinement に返却

### FR-10K-5: Ops UI

- refined Pc 行に propagated バッジ

### FR-10K-6: env チューニング

- 成長率 env（R/T/N per-day）

---

## 3. 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `COV_PROPAGATION_ENABLED` | `false` | 伝播 ON |
| `COV_PROP_R_GROWTH_PER_DAY` | `0.10` | R 軸 km/day |
| `COV_PROP_T_GROWTH_PER_DAY` | `0.05` | T 軸 |
| `COV_PROP_N_GROWTH_PER_DAY` | `0.05` | N 軸 |

---

## 4. スコープ外

- 6×6 STM、CDM σ TCA シフト、PagerDuty、fleet 別 API SLO

---

## 5. 成功条件

1. propagation ON で古い TLE の Pc が static より大きくなるケース
2. pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 10J](requirements-phase10j.md)
- [Phase 10D](requirements-phase10d.md)
