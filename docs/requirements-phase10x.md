# CAS Phase 10X — 要件定義書

**版:** 10X  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10x.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第二十四フェーズ。10W で先送りした breach 状態 DB 永続化と Redis 有効時の metrics + Celery dual push を実装する。

| 変更箇所 | 内容 |
|---------|------|
| DB | `fleet_alert_breach_states` |
| Service | `breach_state_store` DB 層、`should_sync_breaches_on_metrics_scrape` |
| env | `ALERTMANAGER_PUSH_DB_STATE_ENABLED` |

---

## 2. 機能要件

### FR-10X-1: breach DB 永続化

- 優先順位: Redis > DB > in-memory
- opt-in `ALERTMANAGER_PUSH_DB_STATE_ENABLED`

### FR-10X-2: dual push（Redis 時）

- Celery ON + Redis ON 時は `/metrics` scrape からも `sync_breaches` 実行
- Redis 共有状態により重複 fire を防止

---

## 3. スコープ外

- silence チェックボックス bulk、Redis/DB なし dual push

---

## 4. 成功条件

1. DB ON で breach 状態永続化
2. Redis + Celery ON で dual push 安全動作
3. pytest 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 10W](requirements-phase10w.md)
- [Phase 10V](requirements-phase10v.md)
