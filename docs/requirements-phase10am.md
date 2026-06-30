# Phase 10AM — reload 履歴 Redis + dry-run 強化 + 艦隊名フィルタ

## 1. 概要

Phase 10 第三十九フェーズ。10AL でスコープ外とした reload 履歴 Redis 永続化、dry-run 折りたたみ、per-fleet summary 艦隊名フィルタを実装する。

| 区分 | 内容 |
|------|------|
| API | reload history Redis、`fleet_name_contains`、`will_change` |
| UI | dry-run 変更行のみ、艦隊名フィルタ |

---

## 2. 機能要件

### FR-10AM-1: reload 履歴 Redis 永続化

- Redis LIST `cas:prometheus:reload:history`
- `REDIS_URL` あり時は Redis 優先、なければ in-memory
- `PROMETHEUS_RELOAD_HISTORY_REDIS_ENABLED`（default: Redis 設定時 true）

### FR-10AM-2: dry-run 変更なし行折りたたみ

- preview に `will_change: bool`
- Ops UI「変更行のみ」チェック + 変更なし N 件トグル

### FR-10AM-3: per-fleet summary 艦隊名フィルタ

- `GET summary?group_by=fleet&fleet_name_contains=...`
- Ops 全艦隊履歴セクションに艦隊名入力

---

## 3. スコープ外

- reload 履歴 Redis TTL
- dry-run preview CSV エクスポート
- fleet summary ページネーション

---

## 4. 成功条件

1. Redis 永続化 / dry-run 折りたたみ / 艦隊名フィルタが動作
2. Ops UI 反映
3. pytest 全件 PASS（405）

---

## 5. 関連ドキュメント

- [Phase 10AL](requirements-phase10al.md)
