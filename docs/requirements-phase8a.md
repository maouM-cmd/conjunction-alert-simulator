# CAS Phase 8A — 要件定義書

**版:** 8A  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase8a.md`）

---

## 1. 概要

Phase 7A 完了後、Space-Track `cdm_public` を単一衛星 `/conjunctions` 解析に自動統合する。手動 CDM ペーストなしで接近一覧の該当デブリに RTN 共分散 Pc（`sigma_source: cdm_covariance`）を適用。

| 変更箇所 | 内容 |
|---------|------|
| [`cdm_spacetrack_merge.py`](../backend/app/services/cdm_spacetrack_merge.py) | NORAD マッチ + fetch + KVN 化 + enrichment |
| [`analysis.py`](../backend/app/services/analysis.py) | `auto_spacetrack_cdm` 分岐 |
| API / UI | リクエストフラグ、レスポンスメタ、チェックボックス |

---

## 2. 機能要件

### FR-P8A-1: 自動 CDM マージ

- `ConjunctionsRequest.auto_spacetrack_cdm: bool`
- `fetch_cdm_public(norad_id=satellite.norad_id)` → イベントと NORAD マッチ
- RTN あり record: `enrich_record_with_rtn` → `cdm_public_to_kvn` → `apply_cdm_covariance_to_events`
- `use_advanced_pc=true` 必須（encounter plane 経路）

### FR-P8A-2: 互換・フォールバック

- 手動 `cdm_text` がある場合は auto をスキップ（手動優先）
- Space-Track 未設定時: 解析 200、merged=0（503 にしない）
- 任意 `spacetrack_cdm_pc_min` で Pc 下限フィルタ

### FR-P8A-3: レスポンス / UI

- `spacetrack_cdm_records_fetched` / `spacetrack_cdm_events_merged` / `spacetrack_cdm_degraded`
- UI「Space-Track CDM 自動適用」— `spacetrack_configured` 時のみ有効
- 解析メタにマージ件数表示

---

## 3. スコープ外

- v1.2.1 Release tag
- Live Demo への Space-Track 認証

---

## 4. Phase 8A-ext — batch 拡張 — **完了**

- `/conjunctions/batch` に `auto_spacetrack_cdm` を追加（ProcessPool 経由で各衛星に 8A ロジック適用）
- `BatchSummaryOut.spacetrack_cdm_events_merged` / `spacetrack_cdm_satellites_with_merge`
- コンステレーション UI チェックボックス + fleet サマリ表示

---

## 5. 成功条件

1. 認証あり + `auto_spacetrack_cdm=true` で該当デブリが `sigma_source: cdm_covariance`
2. 手動 `cdm_text` パス regression なし
3. 認証なしでも接近解析成功（マージ 0）
4. UI チェック + マージ件数表示
5. `pytest tests/` 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 7A](requirements-phase7a.md) — RTN 取得基盤
- [API 設計](api-design.md)
- [implementation_plan.md](../implementation_plan.md)
