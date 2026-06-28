# CAS v1.4.0 — Phase 9B Scheduled Screening

**Conjunction Alert Simulator** v1.4.0 — Celery + Redis + Beat による艦隊定期スクリーニング。

## ハイライト

- **Phase 9B** — `screening_schedules` / `screening_runs` を PostgreSQL に永続化
- Celery worker + Beat（60 秒 poll）で cron 定期実行
- REST: スケジュール CRUD、手動 Run、`GET /runs` 履歴
- 解析は既存 batch エンジン、完了通知は既存 webhook 経路を再利用
- `docker compose up` で `postgres` + `redis` + `worker` + `beat` 起動

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| Zenn | https://zenn.dev/hukuhukuchan/articles/6bd364012c6bf5 |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 9B 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase9b.md |
| 商用運用ロードマップ | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-commercial-ops.md |

## デモ

![Demo](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/demo.gif)

Screening API（Docker Compose 起動後）:

```powershell
docker compose up --build -d
# 艦隊作成 → 衛星登録 → スケジュール作成
curl -X POST http://localhost:8000/api/v1/screening/schedules \
  -H "Content-Type: application/json" \
  -d "{\"fleet_id\":\"<uuid>\",\"name\":\"Daily\",\"cron_expression\":\"0 0 * * *\"}"
```

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [CHANGELOG](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/CHANGELOG.md)
- [v1.3.0 — Phase 9A Fleet Registry](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.3.0)

**License:** MIT
