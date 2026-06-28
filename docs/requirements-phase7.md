# CAS Phase 7 — 要件定義書

**版:** 7（ロードマップ） / **7C**（初回実装）  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase7.md`）

---

## 1. 概要

Phase 6（ポートフォリオ公開 v1.1.1）完了後の**機能拡張**フェーズ。Phase 6G（Qiita 本文仕上げ）はスキップし、製品価値の向上に移行する。

### Phase 7 焦点（決定）

| 順序 | サブフェーズ | 内容 | 状態 |
|------|-------------|------|------|
| **1** | **7C** | 性能・UX（高度プリフィルタ UI、batch 改善、Live Demo UX） | **完了** |
| **2** | **7A** | Space-Track CDM RTN 共分散の自動取得強化 | **完了** |
| 3 | 7B | Slack Bot / OAuth（Incoming Webhook から Bot へ） | 未着手 |

**7C を最初に選ぶ理由:** 外部 OAuth / Space-Track 認証不要。[`analysis.py`](../backend/app/services/analysis.py) に高度プリフィルタが既にあり UI/API 露出だけで効果が大きい。Live Demo（Render cold start）の体験改善もポートフォリオに直結。

---

## 2. Phase 7C — 機能要件

### FR-P7C-1: 高度プリフィルタの API / UI 露出

- 現状: `run_conjunction_analysis(..., use_altitude_prefilter=True)` は内部のみ（500 件超で ±200 km 帯フィルタ）
- `ConjunctionsRequest` / batch リクエストに `use_altitude_prefilter: bool = True` を追加
- フロント: 「高度帯プリフィルタ」チェックボックス + ツールチップ（全デブリ対象に戻すと遅くなる旨）
- レスポンスメタ: `debris_candidates_count`（フィルタ後件数）を返却

### FR-P7C-2: batch 性能・可観測性

- batch レスポンスに衛星ごとの `computation_time_ms` / `debris_candidates_count` を含める（既存フィールドがあれば統一）
- `BATCH_MAX_WORKERS` の README / `.env.example` 明記
- 任意: 進捗表示（UI に「N/M 衛星完了」— 同期 batch の場合は完了後サマリのみでも可）

### FR-P7C-3: Live Demo UX

- [`LIVE_DEMO_URL.md`](LIVE_DEMO_URL.md) に cold start 注意（初回 30〜60 秒）と推奨操作順を追記
- フロント: cold start 中のローディング文言（`/health` ポーリングまたは初回 fetch 失敗時リトライ 1 回）
- README Live Demo 節に cold start 1 行追記

---

## 3. Phase 7C — スコープ外

- Space-Track CDM フル RTN 自動取得 → **7A**
- Slack Bot OAuth → **7B**
- v1.2.0 tag / 新 Release（実装完了後に別判断）
- Qiita 本文更新（Phase 6G スキップのまま）

---

## 4. Phase 7C — 成功条件

1. UI から高度プリフィルタ ON/OFF が切り替え可能
2. OFF 時は従来どおり全候補（性能劣化は許容、タイムアウトは NFR 準拠）
3. Live Demo 初回アクセス時にユーザーが cold start を理解できる
4. `pytest tests/` 全件 PASS

---

## 5. Phase 7A / 7B（ロードマップ）

### 7A — Space-Track CDM 強化 — **完了**

- 詳細: [requirements-phase7a.md](requirements-phase7a.md)
- `cdm_public` / detail から RTN σ をパースし compare-alert に自動反映
- `CdmPublicRecordOut.has_rtn_covariance`、UI RTN バッジ

### 7B — Slack Bot

- Phase 5C スコープ外だった Slack Bot / OAuth
- Incoming Webhook に加え Bot トークン + チャンネル指定

---

## 6. 関連ドキュメント

- [Phase 7A](requirements-phase7a.md) — Space-Track CDM RTN 共分散
- [Phase 6G](requirements-phase6g.md) — Qiita 仕上げ（スキップ）
- [公開チェックリスト](publish-checklist-v1.1.0.md) — §8 N/A
- [implementation_plan.md](../implementation_plan.md) — 7C 実装方針
