# Live Demo URL (Phase 6C)

**Status:** pending — Render Blueprint 未デプロイ

デプロイ完了後、以下を更新してください。

| 項目 | 値 |
|------|-----|
| Base URL | `https://<your-service>.onrender.com` |
| App URL | `https://<your-service>.onrender.com/app/` |

## 更新手順

1. [deploy-render-phase6c.md](deploy-render-phase6c.md) に従い Render Blueprint デプロイ
2. 検証:

```powershell
venv\Scripts\python -m backend.cli.verify_deploy --url https://<your-service>.onrender.com
```

3. 本ファイルの URL を確定値に更新
4. [`README.md`](../README.md) の **Live Demo** セクションに App URL を追記
