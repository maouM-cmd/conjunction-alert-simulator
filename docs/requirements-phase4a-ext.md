# CAS Phase 4A-Ext — 要件定義書

**版:** 4A-Ext  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase4a-ext.md`）

---

## 1. 概要

Phase 4A で CDM 比較 API に統合した encounter plane / Alfriend / Monte Carlo Pc を、単一衛星 `/conjunctions` と `/conjunctions/batch` に **opt-in** で拡張する。

| サブフェーズ | 内容 |
|-------------|------|
| 4A-Ext-1 | TLE ペア + TCA index から encounter plane Pc（等方 σ） |
| 4A-Ext-2 | API フラグ `use_advanced_pc`、Alfriend を primary Pc |
| 4A-Ext-3 | UI チェックボックス + 一覧に Pc 方式表示 |

---

## 2. 機能要件

### FR-P4A-Ext-1: 共通 Pc サービス

- `pc_conjunction.py` — `pc_for_tle_pair_at_index()`
- σ: 手動指定 > TLE 経過日数推定（CDM なし）
- 共分散: `C_2x2 = σ² I`（等方 encounter）
- bulk 用 Alfriend grid: **80×120**（CDM compare は 150×240 維持）

### FR-P4A-Ext-2: 接近解析 API

| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| `use_advanced_pc` | `false` | `true` 時 encounter Alfriend を適用 |
| primary `pc` | Foster | advanced 時 **Alfriend** |
| MC（bulk） | 上位 **5 件**のみ | Alfriend 降順で MC 10,000 サンプル |

レスポンス拡張（`ConjunctionOut`）:

- `pc_foster`, `pc_alfriend`, `pc_monte_carlo`（optional）
- `pc_method_used`: `foster` | `encounter_advanced`

### FR-P4A-Ext-3: UI

- 単一衛星・コンステレーションに「高精度 Pc (Alfriend encounter plane)」チェックボックス
- 一覧で advanced 時 Foster / Alfriend / MC（あれば）を表示

---

## 3. スコープ外

- 全イベントへの MC 10,000（性能上不可）
- CDM 共分散を一覧 API に自動適用
- scipy 依存

---

## 4. 成功条件

1. `use_advanced_pc=false`（デフォルト）で従来 Foster のみ、性能維持
2. `use_advanced_pc=true` で `pc_method_used: encounter_advanced`、primary Pc = Alfriend
3. 上位 5 件のみ `pc_monte_carlo` が非 null
4. UI チェックボックスで ON/OFF 切替
5. `pytest tests/` 全件 PASS

---

## 5. 関連ファイル

| 種別 | パス |
|------|------|
| Conjunction Pc | `backend/app/services/pc_conjunction.py` |
| 解析統合 | `backend/app/services/analysis.py` |
| API 出力 | `backend/app/services/conjunction_out.py` |
| スキーマ | `backend/app/models/schemas.py` |
| テスト | `tests/test_pc_conjunction.py`, `tests/test_batch_analysis.py` |
