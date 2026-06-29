# CAS Phase 10V — 要件定義書

**版:** 10V  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10v.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第二十二フェーズ。10U で先送りした Redis 共有 breach 状態と Alertmanager silence 削除 API を実装する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `breach_state_store`, `alertmanager_silence_service` 拡張 |
| API | `DELETE /ops/prometheus/alertmanager/silences/{id}` |
| env | `ALERTMANAGER_PUSH_REDIS_STATE_ENABLED` |

---

## 2. 機能要件

### FR-10V-1: Redis 共有 breach 状態

- `cas:am:breach:{fleet_id}:{alertname}` でプロセス間共有
- Redis 不可時は in-memory フォールバック

### FR-10V-2: silence 削除

- `DELETE /api/v2/silence/{id}` 連携
- fleet スコープ認可

---

## 3. 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `ALERTMANAGER_PUSH_REDIS_STATE_ENABLED` | `false` | opt-in |

---

## 4. スコープ外

- silence 一括削除、breach DB 永続化

---

## 5. 成功条件

1. Redis ON でワーカー間 breach 状態共有
2. silence 削除 API が動作
3. pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 10U](requirements-phase10u.md)
- [Phase 10T](requirements-phase10t.md)
