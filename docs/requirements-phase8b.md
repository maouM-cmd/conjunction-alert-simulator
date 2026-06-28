# CAS Phase 8B — 要件定義書

**版:** 8B  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase8b.md`）

---

## 1. 概要

Phase 8A 完了後、Webhook / Slack に加え **SMTP メール** による接近アラート配信経路を追加する。Phase 7B でスコープ外だったメール通知を実装する。

| 配信モード | 必須 env | 送信先 |
|-----------|----------|--------|
| `generic`（既定） | `ALERT_WEBHOOK_URL` | 任意 URL |
| `slack` | `ALERT_WEBHOOK_URL` | Incoming Webhook |
| `slack_bot` | `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID` | Slack Web API |
| **`smtp`**（新規） | `SMTP_HOST`, `SMTP_FROM`, `SMTP_TO` | SMTP サーバ |

---

## 2. 機能要件

### FR-P8B-1: SMTP 配信

- [`webhook_notifier.py`](../backend/app/services/webhook_notifier.py) に `ALERT_WEBHOOK_FORMAT=smtp` を追加
- Python 標準 `smtplib` + `email.message`（新依存なし）
- 任意: `SMTP_PORT`（default 587）、`SMTP_USER` / `SMTP_PASSWORD`、`SMTP_USE_TLS`（default true）

### FR-P8B-2: 通知経路の統合

- 単一衛星 `notify_webhook` / batch fleet 通知 / `send_test_webhook` すべて smtp 対応
- 本文は Slack テキストと同じ `_alert_line` 形式（plain text）
- subject: `CAS conjunction alert` / batch 時 `CAS batch alert`

### FR-P8B-3: 設定判定・互換

- `generic` / `slack` / `slack_bot` の既存挙動は変更なし
- smtp 未設定時: 解析は 200 + noop、テスト ping は 503

### FR-P8B-4: Health

- `HealthResponse.alert_delivery_configured` / `alert_delivery_format: smtp`

---

## 3. スコープ外

- HTML メール / 添付 / 複数 To

---

## 4. 成功条件

1. `smtp` + 必須 env 設定時、`notify_webhook=true` でメール送信
2. generic / slack / slack_bot regression なし
3. `/alerts/webhook/test` が smtp モードで動作
4. `/health` で `alert_delivery_format: smtp`
5. `pytest tests/` 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 7B](requirements-phase7b.md) — Slack Bot（SMTP は当時スコープ外）
- [Phase 8A](requirements-phase8a.md) — CDM auto-merge
- [API 設計](api-design.md)
- [implementation_plan.md](../implementation_plan.md)

---

## 6. Ship v1.2.2 — **完了**

- CHANGELOG / Release Notes / README / Zenn 原稿更新
- `git tag v1.2.2` + GitHub Release
