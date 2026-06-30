# Phase 10AR — row_errors UI + purge async + ページ番号

## 1. 概要

Phase 10 第四十四フェーズ。10AQ でスコープ外とした row_errors プレビュー UI、purge Celery enqueue、fleet summary ページ番号を実装する。

| 区分 | 内容 |
|------|------|
| API | `POST purge?async_run=true` |
| UI | dry-run errors 列、purge async ボタン、ページ N/M |

---

## 2. 機能要件

### FR-10AR-1: row_errors Ops プレビュー表

- preview テーブルに errors 列
- `row_errors` 各行をエラー行として表示
- preview 空でも row_errors があればテーブル表示

### FR-10AR-2: purge Celery enqueue

- `POST /prometheus/reload/history/purge?async_run=true`
- 応答 `queued`, `task_id`
- Ops「reload 履歴 purge (async)」ボタン

### FR-10AR-3: fleet summary ページ番号

- ページング表示: `ページ N/M（offset範囲 / total 件）`

---

## 3. スコープ外（10AS 候補）

- purge async タスク状態ポーリング UI
- row_errors テーブル CSV エクスポート
- fleet summary 最終ページへジャンプ

---

## 4. 成功条件

1. row_errors UI / purge async / ページ番号が動作
2. Ops UI 反映
3. pytest 全件 PASS（435）

---

## 5. 関連ドキュメント

- [Phase 10AQ](requirements-phase10aq.md)
