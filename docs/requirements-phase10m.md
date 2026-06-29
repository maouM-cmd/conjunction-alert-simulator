# CAS Phase 10M — 要件定義書

**版:** 10M  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10m.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第十三フェーズ。CDM RTN 共分散を encounter 平面へ射影する際、SGP4 最接近 index ではなく **CDM 記載 TCA** の軌道状態を使う。

| 変更箇所 | 内容 |
|---------|------|
| Service | `cdm_tca_shift_service` |
| 統合 | `cdm_pc_enrichment`, `cdm_compare`, `pc_refinement_service` |
| API | `covariance_source: cdm_encounter_tca_shift` |
| env | `CDM_TCA_SHIFT_ENABLED` |

---

## 2. 機能要件

### FR-10M-1: TCA シフト

- `CDM_TCA_SHIFT_ENABLED=true` かつ CDM に `TCA` + 共分散があるとき、軌道グリッド上で CDM TCA に最も近い index の状態で encounter Pc を計算

### FR-10M-2: スクリーニング結果の保持

- `miss_distance_km` / screening `tca` は変更しない（Pc 計算用状態のみシフト）

### FR-10M-3: 後方互換

- default OFF で既存 `cdm_encounter` 挙動を維持

### FR-10M-4: 統合経路

- `/conjunctions` + `apply_cdm_covariance`
- CDM compare API
- Space-Track CDM 経由の Pc refinement（`apply_cdm_covariance_to_events` 経由）

---

## 3. 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `CDM_TCA_SHIFT_ENABLED` | `false` | opt-in |

---

## 4. スコープ外

- 6×6 STM、線形補間、fleet 別 API SLO

---

## 5. 成功条件

1. shift ON で `covariance_source=cdm_encounter_tca_shift`
2. shift OFF で既存テスト不変
3. pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 10L](requirements-phase10l.md)
- [Phase 10K](requirements-phase10k.md)
- [Phase 10D](requirements-phase10d.md)
