# Phase 10AT — purge 履歴表示 + preview CSV API + 先頭ページ

## 1. 概要

Phase 10 第四十六フェーズ。10AS でスコープ外とした purge 履歴テーブル表示、preview CSV サーバー API 化、fleet summary 先頭ページを実装する。

| 区分 | 内容 |
|------|------|
| Backend | purge 結果を reload 履歴に記録 |
| UI | preview CSV サーバー経由、先頭へボタン |

---

## 2. 機能要件

### FR-10AT-1: purge 履歴テーブル表示

- async enqueue 時 `source=purge` の PENDING エントリ
- sync purge / Celery beat 完了時に purge 結果を記録
- 履歴一覧で live task status を反映

### FR-10AT-2: preview CSV サーバー API

- `preview CSV` ボタンは `dry_run=true&format=csv` API を使用
- クライアント preview キャッシュ不要
- `changes_only` チェックボックスをクエリに反映

### FR-10AT-3: fleet summary 先頭ページ

- 「先頭へ」ボタン — `offset=0`
- `offset <= 0` 時 disabled

---

## 3. スコープ外（10AU 候補）

- purge 履歴フィルタ（source=purge のみ）
- preview CSV 用専用エンドポイント
- fleet summary ページ直接入力の検証強化

---

## 4. 成功条件

1. purge 履歴 / preview CSV API / 先頭へが動作
2. Ops UI 反映
3. pytest 全件 PASS（445）

---

## 5. 関連ドキュメント

- [Phase 10AS](requirements-phase10as.md)
