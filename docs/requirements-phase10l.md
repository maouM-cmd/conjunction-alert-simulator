# CAS Phase 10L — 要件定義書

**版:** 10L  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10l.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第十二フェーズ。既存 Webhook 通知基盤に PagerDuty Events API v2 を追加する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `webhook_notifier` pagerduty format |
| API | `/health` `alert_delivery_format: pagerduty` |
| env | `PAGERDUTY_ROUTING_KEY` |

---

## 2. 機能要件

### FR-10L-1: フォーマット追加

- `ALERT_WEBHOOK_FORMAT=pagerduty`

### FR-10L-2: Events API v2

- `POST https://events.pagerduty.com/v2/enqueue` で trigger

### FR-10L-3: 全通知経路

- conjunction / batch / new alerts / Pc escalation / mitigation best / auto plan / test ping

### FR-10L-4: severity

- escalation→`critical`, high→`error`, medium→`warning`, test→`info`

### FR-10L-5: 失敗時

- `degraded=True` でログ、本処理継続

---

## 3. 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `ALERT_WEBHOOK_FORMAT` | `generic` | `pagerduty` 追加 |
| `PAGERDUTY_ROUTING_KEY` | — | Events v2 routing key |

---

## 4. スコープ外

- CDM σ TCA シフト、fleet 別 API SLO、PagerDuty resolve/ack

---

## 5. 成功条件

1. pagerduty 設定で test ping + escalation 通知成功
2. pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 10K](requirements-phase10k.md)
- [Phase 10B](requirements-phase10b.md)
