# CAS v1.2.2 — Phase 8B SMTP alerts

**Conjunction Alert Simulator** v1.2.2 — SMTP メールによる接近アラート配信。

## ハイライト

- **Phase 8B** — `ALERT_WEBHOOK_FORMAT=smtp`：`SMTP_HOST` / `SMTP_FROM` / `SMTP_TO` でメール通知
- 単一衛星 / batch fleet / **Webhook テスト** ping すべて対応
- TLS + 認証（`SMTP_USE_TLS`, `SMTP_USER` / `SMTP_PASSWORD`）— 新依存なし（標準 `smtplib`）
- 配信モード 4 種: `generic` / `slack` / `slack_bot` / **`smtp`**

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| Zenn | https://zenn.dev/hukuhukuchan/articles/6bd364012c6bf5 |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 8B 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase8b.md |

## デモ

![Demo](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/demo.gif)

`.env` に SMTP 設定:

1. `ALERT_WEBHOOK_FORMAT=smtp` + `SMTP_*` を設定
2. UI **Webhook テスト** または `POST /api/v1/alerts/webhook/test` で接続確認
3. 接近解析で `notify_webhook: true` → high/medium イベントをメール送信

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [CHANGELOG](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/CHANGELOG.md)
- [v1.2.1 — Phase 8 CDM](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.2.1)

**License:** MIT
