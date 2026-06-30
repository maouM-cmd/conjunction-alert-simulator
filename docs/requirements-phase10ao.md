# Phase 10AO — offset UI + reload purge + dry-run CSV フィルタ

## 1. 概要

Phase 10 第四十一フェーズ。10AN でスコープ外とした fleet summary offset UI、reload 履歴 stale 物理 purge、dry-run CSV changes_only フィルタを実装する。

| 区分 | 内容 |
|------|------|
| API | `import?changes_only=true`、reload Redis purge |
| UI | fleet summary 前へ/次へ、dry-run CSV changes_only 連携 |

---

## 2. 機能要件

### FR-10AO-1: fleet summary offset UI

- Ops ページング行（前へ/次へ）
- `fleetSummaryOffset` 状態 + `limit&offset` API/CSV 連携
- フィルタ変更時 `offset=0` リセット

### FR-10AO-2: reload 履歴 Redis stale 物理 purge

- `_purge_stale_reload_history_redis()`: LRANGE → TTL フィルタ → DEL → LPUSH
- push 成功後・read 開始時に purge
- in-memory も push/read 時に TTL trim

### FR-10AO-3: dry-run CSV changes_only フィルタ

- `POST import?dry_run=true&changes_only=true`
- `will_change=false` 行を preview から除外して CSV/JSON 返却
- Ops「変更行のみ」チェックボックスと dry-run CSV 連携

---

## 3. スコープ外（10AP 候補）

- fleet summary offset 数値直接入力
- reload purge Celery 定期タスク
- dry-run CSV に errors 列エクスポート

---

## 4. 成功条件

1. offset UI / reload purge / changes_only が動作
2. Ops UI 反映
3. pytest 全件 PASS（419）

---

## 5. 関連ドキュメント

- [Phase 10AN](requirements-phase10an.md)
