# CAS Phase 4C — 要件定義書

**版:** 4C  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase4c.md`）

---

## 1. 概要

Phase 4C では CAS を **Docker / docker-compose** でワンコマンド起動可能にし、TLE/CDM キャッシュの永続化と本番向け uvicorn 設定を整える。

| サブフェーズ | 内容 |
|-------------|------|
| 4C-1 | Dockerfile + docker-compose + .dockerignore |
| 4C-2 | 本番 uvicorn（reload なし、workers=1） |
| 4C-3 | deploy.md + README デプロイ手順 |
| 4C-4 | スモークテスト + ship |

---

## 2. 機能要件

### FR-P4C-1: コンテナビルド

- [`Dockerfile`](../Dockerfile) — Python 3.12-slim、backend + frontend + samples
- [`docker-compose.yml`](../docker-compose.yml) — ポート 8000、healthcheck

### FR-P4C-2: キャッシュ永続化

- named volume `cas-cache` → `/app/data/cache`
- TLE / Space-Track CDM JSON キャッシュをコンテナ再起動後も保持

### FR-P4C-3: 公開手順

- [`docs/deploy.md`](deploy.md) — ローカル / LAN 公開
- PaaS（Render / Fly.io）へのデプロイ概要（実行はユーザー側）

---

## 3. スコープ外

- 実クラウドへの自動デプロイ
- HTTPS / リバースプロキシの IaC
- Phase 4D ポートフォリオ素材

---

## 4. 成功条件

1. `docker compose up --build` で `http://localhost:8000/app/` が開ける
2. `/health` が 200 JSON
3. キャッシュ volume がマウントされる
4. `pytest tests/` 全件 PASS

---

## 5. 関連ファイル

| 種別 | パス |
|------|------|
| Docker | `Dockerfile`, `docker-compose.yml`, `.dockerignore` |
| デプロイ手順 | `docs/deploy.md` |
| テスト | `tests/test_app_deploy.py` |
