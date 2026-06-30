# Phase 10AS — purge ポーリング + preview CSV + 最終ページ

## 1. 概要

Phase 10 第四十五フェーズ。10AR でスコープ外とした purge async ポーリング UI、row_errors プレビュー CSV エクスポート、fleet summary 最終ページへジャンプを実装する。

| 区分 | 内容 |
|------|------|
| Backend | purge task ID 登録 + status message マップ |
| UI | purge ポーリング、preview CSV、最後へボタン |

---

## 2. 機能要件

### FR-10AS-1: purge async ポーリング UI

- `queue_purge_stale_prometheus_reload_history` 成功時 `task_id` を `_enqueued_reload_task_ids` に登録
- `get_prometheus_reload_task_status` が purge 結果 `{status, removed, reason}` を message にマップ
- Ops `pollPurgeReloadHistoryTask` — 2s × 15、`GET /reload/tasks/{id}`
- async purge 成功後ポーリング開始、完了後 reload 履歴を再読込

### FR-10AS-2: row_errors プレビュー CSV エクスポート

- dry-run 後 `preview CSV` ボタン有効
- キャッシュ `lastOpsBreachRetentionImportPreview` からクライアント CSV 生成
- `changes_only` 時は preview 行のみフィルタ、row_errors 行は常に含める

### FR-10AS-3: fleet summary 最終ページへ

- 「最後へ」ボタン — `offset = max(0, (ceil(total/limit) - 1) * limit)`
- `offset + limit >= totalRows` 時 disabled

---

## 3. スコープ外（10AT 候補）

- purge async 結果を reload 履歴テーブルに表示
- preview CSV をサーバー API 経由（キャッシュ不要）
- fleet summary 先頭ページへボタン

---

## 4. 成功条件

1. purge ポーリング / preview CSV / 最後へが動作
2. Ops UI 反映
3. pytest 全件 PASS（440）

---

## 5. 関連ドキュメント

- [Phase 10AR](requirements-phase10ar.md)
