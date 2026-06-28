# CAS v1.3.0 — Phase 9A Fleet Registry

**Conjunction Alert Simulator** v1.3.0 — PostgreSQL 上の艦隊／衛星レジストリ（商用運用ロードマップ第一フェーズ）。

## ハイライト

- **Phase 9A** — `fleets` / `satellites` / `tle_revisions` を PostgreSQL に永続化
- REST CRUD: 艦隊登録、衛星 TLE 管理、TLE revision（2 世代）+ rollback
- `docker compose up` で `postgres` + migration 自動適用
- `DATABASE_URL` 未設定環境（Render Free 等）では fleet API のみ 503 — 既存接近解析は従来どおり

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| Zenn | https://zenn.dev/hukuhukuchan/articles/6bd364012c6bf5 |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 9A 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase9a.md |
| 商用運用ロードマップ | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-commercial-ops.md |

## デモ

![Demo](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/demo.gif)

Fleet API（Docker Compose 起動後）:

```powershell
docker compose up --build -d
curl -X POST http://localhost:8000/api/v1/fleets -H "Content-Type: application/json" -d "{\"name\":\"Demo Fleet\"}"
```

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [CHANGELOG](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/CHANGELOG.md)
- [v1.2.2 — Phase 8B](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.2.2)

**License:** MIT
