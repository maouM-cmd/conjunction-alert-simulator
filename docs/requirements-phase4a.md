# CAS Phase 4A — 要件定義書

**版:** 4A  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase4a.md`）

---

## 1. 概要

Phase 4A では CDM RTN 共分散を **encounter plane** に射影し、**Alfriend** と **Monte Carlo** による高精度 Pc を CDM 比較 API/UI に統合する。

| サブフェーズ | 内容 |
|-------------|------|
| 4A-1 | RTN → TEME → encounter plane 2×2 共分散 |
| 4A-2 | Alfriend（数値積分）+ Monte Carlo Pc |
| 4A-3 | CDM 比較 UI で Foster / Alfriend / MC 並列表示 |

---

## 2. 機能要件

### FR-P4A-1: Encounter Plane

- `encounter_plane.py` — RTN/TEME/encounter 変換、2×2 射影
- `encounter_covariance_from_cdm()` — CDM + TCA 状態から `(C_2x2, b_2d)`

### FR-P4A-2: Advanced Pc

- `pc_advanced.py` — `alfriend_pc`, `monte_carlo_pc`, `pc_from_encounter`
- MC サンプル数: 10,000（定数）
- Foster 等方近似も併記

### FR-P4A-3: CDM Compare 拡張

- `pc_methods`: foster / alfriend / monte_carlo
- `pc_method_used`: `foster_only` | `encounter_advanced`
- primary CAS Pc: encounter 時は Alfriend

### FR-P4A-4: UI

- CDM 比較タブに Pc 方式比較テーブル

---

## 3. スコープ外

- 単一衛星 `/conjunctions` への Alfriend/MC 適用（Foster 維持）→ **Phase 4A-Ext で opt-in 対応済み**（[`requirements-phase4a-ext.md`](requirements-phase4a-ext.md)）
- Space-Track CDM API → **Phase 4B で cdm_public 取得対応済み**（[`requirements-phase4b.md`](requirements-phase4b.md)）
- scipy 依存
- クラウドデプロイ

---

## 4. 成功条件

1. `example.cdm` + demo TLE で `pc_methods.alfriend` / `monte_carlo` が返る
2. `pc_method_used: encounter_advanced`
3. Alfriend ≈ MC（5% 以内）
4. UI に 4 方式表示
5. `pytest tests/` 全件 PASS

---

## 5. 関連ファイル

| 種別 | パス |
|------|------|
| Encounter plane | `backend/app/services/encounter_plane.py` |
| Advanced Pc | `backend/app/services/pc_advanced.py` |
| CDM compare | `backend/app/services/cdm_compare.py` |
| テスト | `tests/test_encounter_plane.py`, `tests/test_pc_advanced.py` |
