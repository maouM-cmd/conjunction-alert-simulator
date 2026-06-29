# CAS Phase 10O — 要件定義書

**版:** 10O  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10o.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第十五フェーズ。PagerDuty Events API v2 の acknowledge / resolve を CAS アラート状態遷移と連動する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `webhook_notifier` lifecycle |
| 統合 | `alert_service.transition_alert` |
| env | `PAGERDUTY_LIFECYCLE_ENABLED` |

---

## 2. 機能要件

### FR-10O-1: dedup_key 統一

- `cas-alert-{alert_id}` で trigger / acknowledge / resolve を同一インシデントに紐付け

### FR-10O-2: 新規アラート trigger

- lifecycle ON 時 `notify_new_alerts` はアラートごとに trigger POST

### FR-10O-3: 状態遷移

- `acknowledged` → `event_action: acknowledge`
- `closed` / `false_positive` → `event_action: resolve`

### FR-10O-4: 後方互換

- lifecycle OFF で 10L バッチ trigger 維持

### FR-10O-5: 失敗時

- PD 送信失敗でも DB 遷移は成功、ログのみ

---

## 3. 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `PAGERDUTY_LIFECYCLE_ENABLED` | `false` | opt-in |
| `PAGERDUTY_ROUTING_KEY` | — | 10L 継続 |
| `ALERT_WEBHOOK_FORMAT` | `generic` | `pagerduty` 時のみ |

---

## 4. スコープ外

- PD→CAS 双方向同期、6×6 STM、per-fleet Prometheus アラートルール

---

## 5. 成功条件

1. lifecycle ON で ack/close が PD に反映
2. lifecycle OFF で既存テスト不変
3. pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 10N](requirements-phase10n.md)
- [Phase 10L](requirements-phase10l.md)
