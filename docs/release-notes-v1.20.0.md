# Release v1.20.0 — Phase 10M

**日付:** 2026-06-28

## 概要

CDM RTN 共分散を encounter 平面へ射影する際、SGP4 最接近 index ではなく **CDM 記載 TCA** の軌道状態を使う opt-in 機能を追加。

## 変更

- `CDM_TCA_SHIFT_ENABLED=true` で CDM TCA 近傍の軌道 index を使用
- `covariance_source: cdm_encounter_tca_shift`
- 統合: `cdm_pc_enrichment`、`cdm_compare`、`pc_refinement_service`
- default OFF で既存挙動維持

## テスト

235 passed

## 関連

- [requirements-phase10m.md](requirements-phase10m.md)
