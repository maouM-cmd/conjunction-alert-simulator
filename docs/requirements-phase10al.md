# Phase 10AL — Ops UI 仕上げ + reload 履歴

## 1. 概要

Phase 10 第三十八フェーズ。10AK でスコープ外とした per-fleet summary CSV UI、dry-run 詳細テーブル、reload 履歴一覧を実装する。

| 区分 | 内容 |
|------|------|
| API | `GET /prometheus/reload/history` |
| UI | fleet summary CSV ボタン、dry-run preview テーブル、reload 履歴テーブル |

---

## 2. 機能要件

### FR-10AL-1: per-fleet summary CSV UI

- 全艦隊 breach 履歴セクションに `fleet summary CSV` ボタン
- `GET summary?group_by=fleet&format=csv` をダウンロード

### FR-10AL-2: dry-run プレビュー詳細テーブル

- retention import dry-run 後、`preview[]` を Ops テーブル表示
- 列: 艦隊 / CSV retention / 現在 override / effective
- 変更行は視覚ハイライト

### FR-10AL-3: reload 履歴一覧

- in-memory 直近 N 件（`PROMETHEUS_RELOAD_HISTORY_SIZE` default 20）
- 同期 reload / Celery enqueue を記録
- `GET /prometheus/reload/history?limit=20`（管理者）
- Ops UI に履歴テーブル、reload 操作後に refresh

---

## 3. スコープ外

- reload 履歴 Redis 永続化
- dry-run 変更なし行の折りたたみ
- per-fleet summary CSV 艦隊名フィルタ UI

---

## 4. 成功条件

1. fleet summary CSV / dry-run テーブル / reload 履歴が動作
2. Ops UI 反映
3. pytest 全件 PASS（398）

---

## 5. 関連ドキュメント

- [Phase 10AK](requirements-phase10ak.md)
