# CAS Phase 10P — 要件定義書

**版:** 10P  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10p.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第十六フェーズ。PagerDuty インシデント webhook（acknowledge / resolve）を受信し、`dedup_key=cas-alert-{alert_id}` から CAS アラート状態を同期する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `pagerduty_inbound_service` |
| API | `POST /api/v1/integrations/pagerduty/webhook` |
| 統合 | `alert_service.transition_alert`（ループ防止） |
| env | `PAGERDUTY_INBOUND_SYNC_ENABLED` |

---

## 2. 機能要件

### FR-10P-1: 署名検証

- PagerDuty v3 `X-PagerDuty-Signature`（HMAC-SHA256、raw body）

### FR-10P-2: dedup_key 逆引き

- `cas-alert-{alert_id}` → `ConjunctionAlert` 更新

### FR-10P-3: イベントマッピング

- `incident.acknowledged` → `open` → `acknowledged`
- `incident.resolved` → `acknowledged` / `mitigation_planned` → `closed`；`open` のみなら ack → close 連鎖

### FR-10P-4: ループ防止

- inbound 経路は `skip_pagerduty_outbound=True` で 10O outbound を抑止

### FR-10P-5: 冪等・後方互換

- 既に目標状態なら no-op 200
- `PAGERDUTY_INBOUND_SYNC_ENABLED=false` で 503

---

## 3. 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `PAGERDUTY_INBOUND_SYNC_ENABLED` | `false` | opt-in |
| `PAGERDUTY_WEBHOOK_SIGNING_SECRET` | — | PD webhook 設定の signing secret |

---

## 4. スコープ外

- 6×6 STM、per-fleet Prometheus アラートルール、PD `false_positive` 自動マッピング

---

## 5. 成功条件

1. PD 側 ack/resolve が CAS DB に反映
2. inbound で 10O outbound が発火しない
3. pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 10O](requirements-phase10o.md)
- [Phase 10L](requirements-phase10l.md)
