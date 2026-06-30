# CAS Phase 10AJ — 要件定義書

**版:** 10AJ  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10aj.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第三十六フェーズ。10AI でスコープ外とした summary CSV、retention CSV インポート、reload Celery ポーリング UI を実装する。

| 変更箇所 | 内容 |
|---------|------|
| API | `GET history/summary?format=csv` |
| API | `POST breach-history-settings/import` |
| Service | `reload_task_id` + reload task status |
| UI | summary CSV、retention インポート、reload ポーリング |

---

## 2. 機能要件

### FR-10AJ-1: summary CSV エクスポート

- `GET history/summary?format=csv`
- 列: `day,total,breaching_count`
- history GET と同一フィルタ

### FR-10AJ-2: retention CSV インポート

- `POST /ops/fleets/breach-history-settings/import` — multipart CSV
- export と同一ヘッダー、未知 fleet_id は skip + errors
- 応答: `updated`, `skipped`, `errors`

### FR-10AJ-3: reload Celery ポーリング

- `reload_task_id` を apply / reload 応答に含める
- `GET /ops/prometheus/reload/tasks/{task_id}` — 管理者
- Ops UI — 2s 間隔・最大 15 回ポーリング

### FR-10AJ-4: Ops UI

- breach history 各セクション summary CSV ダウンロード
- retention CSV インポート（file input）
- apply 後 reload タスク完了表示

---

## 3. スコープ外

- 管理者 summary per-fleet 内訳
- retention import dry-run
- reload 手動ボタン分離

---

## 4. 成功条件

1. summary CSV / retention import / reload polling が動作
2. Ops UI 反映
3. pytest 全件 PASS（384）

---

## 5. 関連ドキュメント

- [Phase 10AI](requirements-phase10ai.md)
