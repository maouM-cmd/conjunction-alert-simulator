# CAS v1.7.0 — Phase 9E Platform Baseline

**Conjunction Alert Simulator** v1.7.0 — API Key 認証、監査ログ、/health 拡張。

## ハイライト

- **Phase 9E** — fleet スコープ API Key（`CAS_API_KEY_REQUIRED` デフォルト false）
- 監査ログ: alert 状態遷移、TLE 更新、schedule CRUD（90 日保持）
- `/health` に PostgreSQL / Redis / Celery worker チェック
- Ops UI: 任意 API Key 入力（`X-API-Key`）

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 9E 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase9e.md |

## 有効化例

```powershell
# .env
CAS_API_KEY_REQUIRED=true
CAS_ADMIN_API_KEY=your-admin-secret
```

```powershell
curl -H "X-API-Key: your-admin-secret" -X POST http://localhost:8000/api/v1/fleets -d '{"name":"Prod Fleet"}'
```

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [v1.6.0 — Phase 9D Scale-Out](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.6.0)

**License:** MIT
