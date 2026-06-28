# CAS Phase 9C — 要件定義書

**版:** 9C  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase9c.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 9 第三フェーズ。9B スクリーニング結果から接近アラートを永続化し、オペレータ triage ワークフローと Ops UI を提供する。

| 変更箇所 | 内容 |
|---------|------|
| 新規 DB | `conjunction_alerts` |
| 新規 API | `/api/v1/ops/*` |
| フロント | 「運用 Ops」タブ |
| screening | ingest + 新規 open のみ webhook |

---

## 2. 機能要件

### FR-P9C-1: アラート永続化

- satellite_id, debris_norad, tca, pc, risk_level, screening_run_id

### FR-P9C-2: 状態遷移

- `open` → `acknowledged` → `mitigation_planned` → `closed` / `false_positive`

### FR-P9C-3: 重複抑制

- 同一 sat-debris **±24h** 窓、`open` 行は更新（新規 open 扱いしない）

### FR-P9C-4: Ops UI

- 艦隊サマリ、アラート一覧、状態フィルタ、comment

### FR-P9C-5: 通知

- screening 経路: **新規 open のみ** webhook

---

## 3. スコープ外

- ad-hoc batch からの自動 ingest（screening のみ）
- 9D チャンク / 9E API Key

---

## 4. 成功条件

1. screening run 後に alerts が DB に残る
2. Ops UI で triage 可能
3. pytest 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 9B](requirements-phase9b.md)
- [商用運用ロードマップ](requirements-commercial-ops.md)
