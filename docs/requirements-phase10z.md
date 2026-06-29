# CAS Phase 10Z — 要件定義書

**版:** 10Z  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10z.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第二十六フェーズ。10X で先送りした DB 共有 dual push 拡張と breach 状態 Ops UI 可視化を実装する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `shared_breach_state_enabled`、`list_fleet_breach_states`、`breach_state_backend` |
| Push | `should_sync_breaches_on_metrics_scrape` — Celery ON + DB ON でも metrics push |
| API | `GET /ops/prometheus/alertmanager/breach-states` |
| UI | Ops パネル breach 状態テーブル |

---

## 2. 機能要件

### FR-10Z-1: DB 共有 dual push

- Celery beat ON かつ `ALERTMANAGER_PUSH_DB_STATE_ENABLED=true` のとき `/metrics` scrape からも `sync_breaches` 実行
- Redis 共有時と同様、共有 store で重複 fire 防止

### FR-10Z-2: breach 状態参照 API

- 艦隊単位で `CASFleetOpenAlertsHigh` / `CASFleetHighRiskOpenAlerts` の breach 状態を返す
- store backend（`redis` / `db` / `memory`）を応答に含める

### FR-10Z-3: Ops UI breach 状態

- 艦隊選択時に breach 状態テーブルを表示
- breaching / ok を色分け表示

---

## 3. スコープ外

- breach 状態の手動編集
- 他艦隊横断 breach 一覧

---

## 4. 成功条件

1. Celery ON + DB ON で metrics dual push が動作
2. breach 状態 API が fleet スコープで参照可能
3. Ops UI に breach 状態が表示される
4. pytest 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 10X](requirements-phase10x.md)
- [Phase 10Y](requirements-phase10y.md)
