# CAS Phase 10AH — 要件定義書

**版:** 10AH  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10ah.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第三十四フェーズ。10AG でスコープ外とした Prometheus reload、retention bulk、履歴日付 range を実装する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `reload_prometheus`、apply 連動 |
| Service | `list_fleet_retention_settings` / `bulk_update_fleet_retention` |
| Service | history `since` / `until` フィルタ |
| API | GET/PATCH bulk settings、apply `reloaded` |
| UI | retention 一覧/bulk、since/until、reload 表示 |

---

## 2. 機能要件

### FR-10AH-1: Prometheus reload

- `PROMETHEUS_RELOAD_URL` 設定時、apply 成功後に POST reload
- 任意 Basic Auth env
- `FleetAlertRulesApplyOut.reloaded` / `reload_message`

### FR-10AH-2: retention bulk

- `GET /ops/fleets/breach-history-settings` — 管理者、全 active 艦隊
- `PATCH /ops/fleets/breach-history-settings/bulk` — 複数艦隊一括更新

### FR-10AH-3: 履歴日付 range

- `GET history?since=&until=` — ISO8601、`since <= until`
- 単艦隊 + 管理者横断 + CSV

### FR-10AH-4: Ops UI

- retention 一覧テーブル + 一括適用
- since/until datetime-local
- apply 後 reload ステータス

---

## 3. スコープ外

- reload リトライ / Celery 非同期
- retention CSV エクスポート
- breach 履歴日次集計 API

---

## 4. 成功条件

1. apply + reload / bulk retention / since-until が動作
2. Ops UI 反映
3. pytest 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 10AG](requirements-phase10ag.md)
