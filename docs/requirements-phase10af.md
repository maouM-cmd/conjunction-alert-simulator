# CAS Phase 10AF — 要件定義書

**版:** 10AF  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10af.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第三十二フェーズ。10AE でスコープ外とした per-fleet 履歴 purge、breaching 艦隊 rule フィルタ、Ops UI を実装する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `purge_old_breach_history(fleet_id)`、Celery 艦隊ループ |
| Service | `fleet_has_breaching_alert` |
| API | `breaching_fleets_only`、`DELETE history` purge |
| UI | fleet-alert-rules ダウンロードセクション |

---

## 2. 機能要件

### FR-10AF-1: per-fleet 履歴 purge

- `purge_old_breach_history(db, fleet_id=None)` — 艦隊スコープ削除
- Celery — active 艦隊ごとに purge、`by_fleet` 集計

### FR-10AF-2: DELETE history purge API

- `DELETE breach-states/history?fleet_id=` — fleet スコープ
- `fleet_id` 省略 — 管理者のみ全艦隊 purge

### FR-10AF-3: breaching 艦隊 rule フィルタ

- `GET fleet-alert-rules?breaching_fleets_only=true` — breach 中艦隊のみ
- `breaching_only`（gauge expr）と併用可

### FR-10AF-4: Ops UI

- ルール雛形ダウンロード（yaml/json）
- breach Gauge expr / breaching 艦隊のみチェックボックス

---

## 3. スコープ外

- 艦隊別 retention 日数（DB 設定）
- rule 雛形の Alertmanager 直接 apply
- 履歴 alertname 複数選択フィルタ

---

## 4. 成功条件

1. per-fleet purge が他艦隊に影響しない
2. DELETE purge API + breaching_fleets_only が動作
3. Ops UI 反映
4. pytest 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 10AE](requirements-phase10ae.md)
