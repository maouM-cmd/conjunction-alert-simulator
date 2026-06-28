# CAS Phase 7B — 要件定義書

**版:** 7B  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase7b.md`）

---

## 1. 概要

Phase 7A 完了後、Incoming Webhook に加え **Slack Bot Token + chat.postMessage** による通知経路を追加する。既存 `generic` / `slack`（Incoming Webhook）は互換維持。

| 配信モード | 必須 env | 送信先 |
|-----------|----------|--------|
| `generic`（既定） | `ALERT_WEBHOOK_URL` | 任意 URL |
| `slack` | `ALERT_WEBHOOK_URL` | Incoming Webhook |
| **`slack_bot`**（新規） | `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID` | Slack Web API |

---

## 2. 機能要件

### FR-P7B-1: Slack Bot 配信

- [`webhook_notifier.py`](../backend/app/services/webhook_notifier.py) に `ALERT_WEBHOOK_FORMAT=slack_bot` を追加
- `POST https://slack.com/api/chat.postMessage`（Bearer Token + channel + text）
- Slack API `ok: false` 時は `degraded=True` + エラーメッセージ

### FR-P7B-2: 設定判定・互換

- format ごとに必須 env を検証（`slack_bot` 時は URL 不要）
- `generic` / `slack` の既存挙動は変更なし
- テスト ping / 解析 `notify_webhook` / batch 通知すべて Bot モード対応

### FR-P7B-3: Health / UI

- `HealthResponse.alert_delivery_configured` / `alert_delivery_format`
- UI 起動時ステータスに配信モード表示（秘密値は返さない）

---

## 3. Slack App セットアップ（ユーザー側）

1. [api.slack.com](https://api.slack.com/apps) で App 作成
2. OAuth Scopes: `chat:write`（公開チャンネル投稿なら `chat:write.public` も可）
3. ワークスペースにインストール → **Bot User OAuth Token**（`xoxb-...`）取得
4. 投稿先チャンネル ID（`C...`）を Slack からコピー
5. `.env` に `ALERT_WEBHOOK_FORMAT=slack_bot`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID` を設定

---

## 4. スコープ外

- `/slack/oauth/install` 等のマルチテナント OAuth フロー
- Block Kit リッチメッセージ
- メール SMTP
- v1.2.0 Release tag

---

## 5. 成功条件

1. `slack_bot` + Token/Channel 設定時、`notify_webhook=true` で Slack チャンネルに投稿
2. Incoming Webhook（`slack`）・generic は従来どおり動作
3. Webhook テスト / `/alerts/webhook/test` が Bot モードでも動作
4. UI または `/health` で配信モードが分かる
5. `pytest tests/` 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 7 ロードマップ](requirements-phase7.md)
- [API 設計](api-design.md)
- [implementation_plan.md](../implementation_plan.md)
