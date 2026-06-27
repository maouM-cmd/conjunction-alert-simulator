# CAS Phase 3 — 要件定義書

**版:** 3.0  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase3.md`）

---

## 1. 概要

Phase 3 では Phase 2 の Pc 計算・接近解析基盤を拡張し、**CDM インポート（3A）** と **複数衛星一括監視（3B）** を実装する。

| サブフェーズ | 内容 |
|-------------|------|
| 3A | CCSDS CDM テキスト解析、外部 Pc/miss distance と CAS 計算値の比較 |
| 3B | 最大 10 衛星の TLE 一括接近解析、衛星別ダッシュボード |

---

## 2. 機能要件

### FR-P3-1: CDM パーサ（3A）

- CCSDS 508.0-B-1 形式の key=value テキストを解析
- 必須フィールド: `TCA`, `MISS_DISTANCE`, `RELATIVE_SPEED`, `COLLISION_PROBABILITY`, `SAT1_OBJECT`, `SAT2_OBJECT`
- 実装: `backend/app/services/cdm_parser.py`
- サンプル: `samples/example.cdm`

### FR-P3-2: CDM 比較 API（3A）

| エンドポイント | 概要 |
|---------------|------|
| `POST /api/v1/cdm/parse` | CDM テキスト → 構造化 JSON |
| `POST /api/v1/cdm/compare` | CDM + TLE ペア → 外部値 vs CAS 計算 |

比較レスポンスに `delta_miss_km`, `delta_pc_ratio` を含む。

### FR-P3-3: CDM UI（3A）

- タブ「CDM 比較」: CDM テキスト + 衛星/デブリ TLE 入力
- 外部 Pc vs CAS Pc、miss distance 差分を並列表示
- デモ読込ボタン（`example.cdm` + demo TLE ペア）

### FR-P3-4: 一括接近解析（3B）

- デブリカタログ取得は **1 回のみ**（`fetch_debris_catalog` 再利用）
- 衛星ごとに `run_conjunction_analysis` を呼び出し
- 上限: **10 衛星**
- 実装: `backend/app/services/batch_analysis.py`

### FR-P3-5: Batch API（3B）

| エンドポイント | 概要 |
|---------------|------|
| `POST /api/v1/conjunctions/batch` | TLE 配列 → 衛星別接近イベント + 全体サマリー |

サマリー: `total_events`, `highest_pc`, `highest_pc_satellite`, `highest_pc_debris`

### FR-P3-6: コンステレーション UI（3B）

- タブ切替: 単一衛星 | コンステレーション | CDM
- 複数 TLE 入力（`---` 区切り）
- 衛星選択ドロップダウン → 既存 3D/回避 UI に連動
- サンプル: `samples/constellation-demo.tle`

---

## 3. 非機能要件

| 項目 | 値 |
|------|-----|
| 単一衛星タイムアウト | 90 秒 |
| 一括解析タイムアウト | 600 秒 |
| 最大衛星数 | 10 |
| 並列化 | Phase 3.5 で検討 |

---

## 4. スコープ外

- Monte Carlo Pc / Alfriend 公式
- CDM 自動生成・Space-Track CDM API 直接取得
- 10 衛星超の batch / 並列化
- クラウドデプロイ

---

## 5. 成功条件

1. `example.cdm` を POST `/cdm/parse` すると構造化 JSON が返る
2. `/cdm/compare` で CDM の Pc/miss distance と CAS 計算値が並列表示される
3. 3〜5 衛星 TLE を batch 送信し、衛星別接近一覧が返る
4. UI でコンステレーション一括解析 → 衛星選択 → 3D 表示が動作
5. `pytest tests/` 全件 PASS

---

## 6. 関連ファイル

| 種別 | パス |
|------|------|
| CDM パーサ | `backend/app/services/cdm_parser.py` |
| CDM 比較 | `backend/app/services/cdm_compare.py` |
| Batch 解析 | `backend/app/services/batch_analysis.py` |
| API | `backend/app/routers/cdm.py`, `batch.py` |
| テスト | `tests/test_cdm_parser.py`, `tests/test_batch_analysis.py` |
