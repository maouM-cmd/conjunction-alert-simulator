# CAS Phase 6B — 要件定義書

**版:** 6B  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase6b.md`）

---

## 1. 概要

Phase 6C（Render Live Demo 稼働）完了後、GitHub Actions で main / tag push 時に pytest → Render Deploy Hook → `verify_deploy` を実行する CI/CD を追加する。

| サブフェーズ | 内容 |
|-------------|------|
| 6B-1 | GitHub Actions `deploy.yml`（pytest → deploy → verify） |
| 6B-2 | Render Deploy Hook 手順 + GitHub Secrets |
| 6B-3 | デプロイ後 `verify_deploy` リトライ |
| 6B-4 | README バッジ + deploy-cloud 追記 |

---

## 2. 機能要件

### FR-P6B-1: deploy workflow

- [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml)
- トリガ: `push` main / tags `v*`、`workflow_dispatch`
- PR では実行しない（[`.github/workflows/test.yml`](../.github/workflows/test.yml) を維持）

### FR-P6B-2: Render Deploy Hook

- GitHub Secret: `RENDER_DEPLOY_HOOK_URL`
- 手順: [`docs/deploy-render-cicd.md`](deploy-render-cicd.md)
- Secret 未設定時: `deploy` job skip、`verify` は実行

### FR-P6B-3: デプロイ検証

- [`backend/cli/verify_deploy.py`](../backend/cli/verify_deploy.py) を CI から実行
- 対象 URL: `https://conjunction-alert-simulator.onrender.com`
- 最大 8 回リトライ（60 秒間隔）

### FR-P6B-4: ドキュメント

- README deploy バッジ
- [`docs/deploy-cloud.md`](deploy-cloud.md) Phase 6B 節

---

## 3. スコープ外

- Fly.io CI
- Render Starter+ disk
- Slack / GitHub デプロイ通知
- Render API によるサービス作成・設定変更

---

## 4. 成功条件

1. `main` push 後、Actions **deploy** workflow で pytest green
2. `RENDER_DEPLOY_HOOK_URL` 設定後、Hook POST + verify_deploy green
3. tag `v*` push でも同パイプライン実行
4. Secret 未設定でも pytest + verify が走る（deploy skip）

---

## 5. 関連ドキュメント

- [Phase 6C](requirements-phase6c.md) — Live Demo URL
- [Render CI/CD 手順](deploy-render-cicd.md)
- [Live Demo URL](LIVE_DEMO_URL.md)
