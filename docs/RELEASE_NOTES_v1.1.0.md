# CAS v1.1.0 — Phase 5 cloud, ops, demo refresh

**Conjunction Alert Simulator** v1.1.0 — クラウドデプロイ manifest、運用 Webhook、CDM σ 一覧 API、デモ素材刷新。

## ハイライト

- **Phase 5B — Cloud** — Render/Fly manifest、同一オリジン API、動的 `PORT`
- **Phase 5C — Ops** — Slack Incoming Webhook、`cdm_text` + CDM encounter σ on `/conjunctions`、batch Webhook
- **Phase 5D — Demo** — Advanced Pc デモペア、`demo.gif` Phase 5 版、Zenn 原稿更新

## 移行メモ

任意の `.env` 追加:

```env
ALERT_WEBHOOK_FORMAT=slack
```

既存 `ALERT_WEBHOOK_URL` の generic JSON 互換は維持（デフォルト `generic`）。

## デモ

![Demo](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/demo.gif)

```powershell
docker compose up --build -d
```

→ http://localhost:8000/app/ — **デモ TLE 読込** → **高精度 Pc** ON → **接近解析**

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [クラウドデプロイ](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/deploy-cloud.md)
- [CHANGELOG](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/CHANGELOG.md)

**License:** MIT
