# Phase 10AN — reload TTL + dry-run CSV + fleet summary ページング

## 1. 概要

Phase 10 第四十フェーズ。10AM でスコープ外とした reload 履歴 Redis TTL、dry-run preview CSV、fleet summary limit/offset を実装する。

| 区分 | 内容 |
|------|------|
| API | reload TTL、`import?dry_run&format=csv`、summary limit/offset |
| UI | dry-run CSV ボタン、fleet summary 件数入力 |

---

## 2. 機能要件

### FR-10AN-1: reload 履歴 Redis TTL

- `PROMETHEUS_RELOAD_HISTORY_REDIS_TTL_SECONDS`（default 604800、`0` で無効）
- push 時 `EXPIRE`、read 時 `enqueued_at` フィルタ

### FR-10AN-2: dry-run preview CSV

- `POST import?dry_run=true&format=csv`
- ヘッダーに `will_change` 列
- Ops dry-run CSV ボタン

### FR-10AN-3: fleet summary limit/offset

- `GET summary?group_by=fleet&limit=&offset=`
- JSON 応答に `limit`, `offset`, `total_rows`
- Ops fleet summary 件数入力

---

## 3. スコープ外

- fleet summary offset UI（次へ/前へ）
- reload 履歴 stale エントリ物理 purge
- dry-run CSV will_change フィルタ

---

## 4. 成功条件

1. TTL / dry-run CSV / summary paging が動作
2. Ops UI 反映
3. pytest 全件 PASS（412）

---

## 5. 関連ドキュメント

- [Phase 10AM](requirements-phase10am.md)
