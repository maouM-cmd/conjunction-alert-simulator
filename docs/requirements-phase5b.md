# CAS Phase 5B — 要件定義書

**版:** 5B  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase5b.md`）

---

## 1. 概要

Phase 5A 完了後、Render / Fly.io 向けクラウドデプロイ manifest と同一オリジン API 修正を行い、公開 URL から Live Demo 可能にする。

| サブフェーズ | 内容 |
|-------------|------|
| 5B-1 | フロント API 同一オリジン + Dockerfile PORT |
| 5B-2 | render.yaml + fly.toml |
| 5B-3 | deploy-cloud.md + README Live Demo |
| 5B-4 | テスト + ship |

---

## 2. 機能要件

### FR-P5B-1: 同一オリジン API

- [`frontend/js/app.js`](../frontend/js/app.js) — port 8080 静的サーバ時のみ `localhost:8000`、それ以外は same origin

### FR-P5B-2: Docker PORT

- [`Dockerfile`](../Dockerfile) — `PORT` 環境変数（デフォルト 8000）

### FR-P5B-3: PaaS manifest

- [`render.yaml`](../render.yaml) — web / docker / health / disk
- [`fly.toml`](../fly.toml) — http_service / health / volume mount

### FR-P5B-4: ドキュメント

- [`docs/deploy-cloud.md`](deploy-cloud.md) — step-by-step
- README Live Demo セクション

---

## 3. スコープ外

- カスタムドメイン / CDN
- GitHub Actions 自動デプロイ
- ユーザーアカウントでの実デプロイ実行（手順まで）

---

## 4. 成功条件

1. `https://<host>/app/` から接近解析が動く
2. manifest + 手順ドキュメント完備
3. 永続キャッシュ mount 設定あり
4. `pytest tests/` 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 5A](requirements-phase5a.md) — Render/Fly 常時公開 → 本フェーズで対応
- [deploy.md](deploy.md) — ローカル Docker
