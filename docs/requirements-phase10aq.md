# Phase 10AQ — offset Enter + reload purge API + dry-run JSON errors

## 1. 概要

Phase 10 第四十三フェーズ。10AP でスコープ外とした offset Enter キー、reload purge 手動 API、dry-run JSON structured errors を実装する。

| 区分 | 内容 |
|------|------|
| API | `POST /prometheus/reload/history/purge`、`row_errors[]` |
| UI | offset Enter、reload 履歴 purge ボタン |

---

## 2. 機能要件

### FR-10AQ-1: offset Enter キー

- fleet summary offset 入力で Enter → 移動ボタンと同じ `goToFleetSummaryOffset()`

### FR-10AQ-2: reload purge 手動 API

- `POST /api/v1/ops/prometheus/reload/history/purge`（管理者のみ）
- 応答 `PrometheusReloadHistoryPurgeOut`: `status`, `removed`, `reason`
- Ops「reload 履歴 purge」ボタン

### FR-10AQ-3: dry-run JSON structured errors

- `FleetBreachHistorySettingsImportOut.row_errors[]`（`fleet_id`, `message`）
- unknown fleet のみでも JSON 200 + `row_errors`

---

## 3. スコープ外（10AR 候補）

- purge API の Celery enqueue オプション
- row_errors の Ops プレビュー表表示
- fleet summary ページ番号表示

---

## 4. 成功条件

1. Enter / purge API / row_errors が動作
2. Ops UI 反映
3. pytest 全件 PASS（430）

---

## 5. 関連ドキュメント

- [Phase 10AP](requirements-phase10ap.md)
