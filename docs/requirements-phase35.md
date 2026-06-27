# CAS Phase 3.5 — 要件定義書

**版:** 3.5  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase35.md`）

---

## 1. 概要

Phase 3.5 では **CDM 共分散を Pc に反映**し、**batch 並列化**と**衛星数上限拡張**を行う。

| サブフェーズ | 内容 |
|-------------|------|
| 3.5A | CDM RTN 共分散 → σ 推定 → CAS Pc 精度向上 |
| 3.5B | ProcessPool による batch 並列解析 |
| 3.5C | 最大衛星数 10 → 25 |

---

## 2. 機能要件

### FR-P35-1: CDM RTN 共分散パース

- フィールド: `SAT1_CR_R`, `SAT1_CT_T`, `SAT1_CN_N`, `SAT2_*`（km²）
- 実装: `backend/app/services/cdm_covariance.py`
- `cdm_parser.py` の `CdmRecord.covariance` に格納

### FR-P35-2: σ 推定と CDM 比較

- `sigma_from_cdm_rtn()` — RTN 標準偏差の RSS 合成
- σ 優先順位: 手動 `sigma_km` > CDM 共分散 > TLE 経過日数
- API レスポンス: `cas_sigma_km`, `sigma_source`

### FR-P35-3: Batch 並列化

- `ProcessPoolExecutor` で衛星ごと解析
- デブリカタログは 1 回取得、ワーカーに渡す
- 結果順序は入力 TLE 順を保持
- `parallel=False` で逐次フォールバック
- 環境変数 `BATCH_MAX_WORKERS`

### FR-P35-4: 衛星数拡張

- `MAX_SATELLITES`: 25
- API / UI / サンプル TLE を更新

---

## 3. 非機能要件

| 項目 | 値 |
|------|-----|
| batch タイムアウト | 600 秒（維持） |
| 最大衛星数 | 25 |
| 並列ワーカー | `min(衛星数, cpu_count, BATCH_MAX_WORKERS)` |

---

## 4. スコープ外

- Monte Carlo Pc / Alfriend 公式
- encounter plane 完全共分散射影
- 25 衛星超 / 分散ワーカー
- クラウドデプロイ

---

## 5. 成功条件

1. `example.cdm` 共分散付きで `/cdm/compare` → `sigma_source: cdm_covariance`
2. batch 6 衛星が並列実行可能（`parallel: true`）
3. 25 衛星まで API/UI が受理
4. `pytest tests/` 全件 PASS

---

## 6. 関連ファイル

| 種別 | パス |
|------|------|
| CDM 共分散 | `backend/app/services/cdm_covariance.py` |
| Batch 並列 | `backend/app/services/batch_analysis.py` |
| テスト | `tests/test_cdm_covariance.py`, `tests/test_batch_analysis.py` |
