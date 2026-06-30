# Phase 10AP — offset 入力 + reload purge 定期 + dry-run errors CSV

## 1. 概要

Phase 10 第四十二フェーズ。10AO でスコープ外とした fleet summary offset 数値入力、reload purge Celery 定期タスク、dry-run CSV errors 列を実装する。

| 区分 | 内容 |
|------|------|
| API | dry-run CSV `errors` 列、reload purge Celery beat |
| UI | fleet summary offset 入力 + 移動ボタン |

---

## 2. 機能要件

### FR-10AP-1: fleet summary offset 数値入力

- ページング行に offset 数値入力 + 移動ボタン
- `0 <= offset < total_rows` にクランプ
- フィルタ/limit 変更時 offset リセット

### FR-10AP-2: reload purge Celery 定期タスク

- `purge_stale_prometheus_reload_history` Celery task
- beat 日次（`PROMETHEUS_RELOAD_HISTORY_PURGE_INTERVAL_SECONDS` optional）
- TTL/Redis 無効時 skipped

### FR-10AP-3: dry-run CSV errors 列

- preview CSV ヘッダーに `errors` 列
- unknown fleet 等は error 行として出力
- `changes_only=true` でも error 行は残す

---

## 3. スコープ外（10AQ 候補）

- offset 入力 Enter キー対応
- reload purge 手動トリガー Ops API
- dry-run JSON structured errors

---

## 4. 成功条件

1. offset 入力 / purge beat / CSV errors が動作
2. Ops UI 反映
3. pytest 全件 PASS（425）

---

## 5. 関連ドキュメント

- [Phase 10AO](requirements-phase10ao.md)
