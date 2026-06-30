# CAS Phase 10AK — 要件定義書

**版:** 10AK  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10ak.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第三十七フェーズ。10AJ でスコープ外とした per-fleet summary、retention import dry-run、reload 手動 UI を実装する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `summarize_all_history_by_fleet` |
| API | `GET summary?group_by=fleet`、`POST import?dry_run=true` |
| UI | per-fleet summary テーブル、dry-run、Prometheus reload ボタン |

---

## 2. 機能要件

### FR-10AK-1: 管理者 summary per-fleet 内訳

- `GET history/summary?group_by=fleet` — 管理者横断のみ
- `fleet_id` 指定時 422
- CSV 列: `day,fleet_id,fleet_name,total,breaching_count`

### FR-10AK-2: retention import dry-run

- `POST import?dry_run=true` — parse + preview、DB 不変
- 応答 `preview[]`: fleet_id, fleet_name, retention_days, current/effective

### FR-10AK-3: reload 手動 UI

- Ops「Prometheus reload」ボタン + 専用 status
- `POST /ops/prometheus/reload` + 既存 task ポーリング

---

## 3. スコープ外

- per-fleet summary 専用 CSV UI トグル
- dry-run 結果テーブル詳細
- reload 履歴一覧

---

## 4. 成功条件

1. per-fleet summary / dry-run / reload 手動 UI が動作
2. Ops UI 反映
3. pytest 全件 PASS（391）

---

## 5. 関連ドキュメント

- [Phase 10AJ](requirements-phase10aj.md)
