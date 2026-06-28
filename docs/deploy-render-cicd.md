# Phase 6B — Render CI/CD 手順

**対象:** GitHub Actions [`deploy.yml`](../.github/workflows/deploy.yml) — main / tag push → pytest → Render Deploy Hook → verify_deploy

Live Demo: https://conjunction-alert-simulator.onrender.com/app/

---

## 1. Render Deploy Hook 取得

1. [Render Dashboard](https://dashboard.render.com/) → Web Service **conjunction-alert-simulator**
2. **Settings** → **Deploy Hook** → **Create Deploy Hook**（未作成の場合）
3. Hook URL をコピー（`https://api.render.com/deploy/srv-...?key=...` 形式）

---

## 2. GitHub Secret 設定

1. https://github.com/maouM-cmd/conjunction-alert-simulator/settings/secrets/actions
2. **New repository secret**
3. Name: `RENDER_DEPLOY_HOOK_URL`
4. Value: 上記 Deploy Hook URL

Secret 未設定時: `deploy` job は skip、`test` + `verify` は実行されます。

---

## 3. Auto-Deploy との関係

Render の **Auto-Deploy**（GitHub 連携）が ON の場合、`main` push で Render 側も自動ビルドが走ります。

| 運用 | 説明 |
|------|------|
| Auto-Deploy ON + Hook | push ごとに二重トリガーの可能性あり。verify が主目的なら許容 |
| Hook のみ | Auto-Deploy OFF → GitHub Actions から Hook POST のみ |

---

## 4. ワークフロー概要

| Job | 条件 | 内容 |
|-----|------|------|
| test | 常時 | `pytest tests/` |
| deploy | Secret あり | `curl -X POST` Deploy Hook |
| verify | test 成功 | 初回 3 分待機 → verify_deploy 最大 8 回 |

手動実行: GitHub **Actions** → **deploy** → **Run workflow**

---

## 5. ローカル検証

```powershell
venv\Scripts\python -m backend.cli.verify_deploy --url https://conjunction-alert-simulator.onrender.com
```

---

## 関連

- [Phase 6B 要件](requirements-phase6b.md)
- [Phase 6C デプロイ](deploy-render-phase6c.md)
- [Live Demo URL](LIVE_DEMO_URL.md)
