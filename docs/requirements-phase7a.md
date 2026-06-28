# CAS Phase 7A — 要件定義書

**版:** 7A  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase7a.md`）

---

## 1. 概要

Phase 7C 完了後、Space-Track `cdm_public` から RTN 共分散を取得・KVN 化し、`compare-alert` の Pc 精度を向上させる。Phase 5C スコープ外だった「Space-Track フル CDM（RTN 共分散）自動取得」を実装する。

| 変更箇所 | 内容 |
|---------|------|
| [`spacetrack_cdm_fetcher.py`](../backend/app/services/spacetrack_cdm_fetcher.py) | RTN フィールド、`fetch_cdm_detail`、24h キャッシュ |
| [`cdm_export.py`](../backend/app/services/cdm_export.py) | `cdm_public_to_kvn` に `SAT1_CR_R` 等を出力 |
| [`cdm_alert_compare.py`](../backend/app/services/cdm_alert_compare.py) | RTN 無し時 lazy detail 取得 |
| API / UI | `has_rtn_covariance`、RTN バッジ、compare 結果表示 |

---

## 2. 機能要件

### FR-P7A-1: Space-Track 取得拡張

- `CdmPublicRecord` に optional RTN フィールド（`RtnVariance`）
- 一覧 JSON に `SAT1_CR_R` / `SAT1_CT_T` / クロス項があればパース（`m**2` → km²）
- `fetch_cdm_detail(cdm_id)` — 一覧に RTN が無い場合の詳細取得（24h キャッシュ）
- 認証未設定時は既存と同様 `RuntimeError` / API **503**

### FR-P7A-2: KVN エクスポート

- `cdm_public_to_kvn(record)` — RTN あり時は `SAT1_CR_R = ... km2` 等を出力（非等方対応）
- `RELATIVE_SPEED` は取得できれば追加

### FR-P7A-3: compare-alert 強化

- レコードに RTN が無ければ `fetch_cdm_detail` を試行し enriched record で KVN 化
- RTN 付き KVN 経路で `sigma_source: cdm_covariance` を返却

### FR-P7A-4: API / UI

- `CdmPublicRecordOut.has_rtn_covariance: bool`
- CDM アラート一覧: RTN 有無バッジ（`RTN σ` / `要詳細`）
- compare-alert 結果で `sigma_source === "cdm_covariance"` を明示

---

## 3. スコープ外

- 7B Slack Bot OAuth
- 単一衛星 `/conjunctions` への Space-Track 自動 CDM マージ
- v1.2.0 Release tag
- Live Demo への Space-Track 認証設定（ユーザー `.env` のみ）

---

## 4. 成功条件

1. Space-Track 認証あり時、RTN 付き CDM レコードで `compare-alert` が `sigma_source: cdm_covariance` を返す
2. RTN なし一覧レコードでも detail 取得で RTN 化できる（取得不可時は従来どおり degraded）
3. UI に RTN 有無が分かる
4. `pytest tests/` 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 7 ロードマップ](requirements-phase7.md)
- [API 設計](api-design.md) — `CdmPublicRecordOut.has_rtn_covariance`
- [implementation_plan.md](../implementation_plan.md)
