# CAS デプロイ手順

**対象:** Phase 4C — Docker / docker-compose

---

## 前提

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)（または Docker Engine + Compose v2）
- ポート **8000** が空いていること

---

## クイックスタート

```powershell
cd C:\Users\admin\OneDrive\ドキュメント\conjunction-alert-simulator

# 任意: Space-Track 利用時
copy .env.example .env
# .env を編集（SPACE_TRACK_USER / PASSWORD）

docker compose up --build -d
```

### 確認

```powershell
curl http://localhost:8000/health
```

ブラウザで UI を開く:

- **http://localhost:8000/app/**

API ドキュメント:

- **http://localhost:8000/docs**

### 停止

```powershell
docker compose down
```

キャッシュを残す場合は `down` のみ（volume `cas-cache` は削除されない）。完全削除:

```powershell
docker compose down -v
```

---

## 構成

| 項目 | 値 |
|------|-----|
| イメージ | プロジェクト直下 `Dockerfile` からビルド |
| ポート | `8000:8000` |
| キャッシュ | volume `cas-cache` → `/app/data/cache` |
| プロセス | uvicorn 1 worker（batch ProcessPool と競合回避） |

---

## 環境変数

`.env`（任意）:

| 変数 | 説明 |
|------|------|
| `SPACE_TRACK_USER` / `SPACE_TRACK_PASSWORD` | Space-Track 認証 |
| `TLE_PROVIDER` | `celestrak`（デフォルト）または `spacetrack` |
| `CAS_HOST` | バインドアドレス（デフォルト `0.0.0.0`） |
| `CAS_PORT` | ポート（デフォルト `8000`） |
| `BATCH_MAX_WORKERS` | batch 並列数（Docker では 2 程度推奨） |

---

## トラブルシュート

| 症状 | 対処 |
|------|------|
| 初回接近解析が遅い | CelesTrak から TLE カタログ取得中。2 回目以降はキャッシュで高速化 |
| `/cdm/fetch` が 503 | `.env` に Space-Track 認証未設定 |
| 504 タイムアウト | 閾値を広げる、または `duration_days` を短くする |
| `.env` が無いと compose が警告 | `copy .env.example .env` で空ファイルでも可 |

---

## クラウドデプロイ（Render / Fly.io）

Phase 5B で manifest を同梱。詳細手順: **[deploy-cloud.md](deploy-cloud.md)**

| プラットフォーム | ファイル |
|-----------------|---------|
| Render Blueprint | [`render.yaml`](../render.yaml) |
| Fly.io | [`fly.toml`](../fly.toml) |

1. GitHub リポジトリを接続して Docker デプロイ
2. 永続ストレージを `/app/data/cache` にマウント
3. 公開 URL の **`/app/`** を Live Demo として使用

Free tier ではスリープ・初回 TLE 取得遅延に注意。閾値 50 km 推奨。

---

## 開発 vs Docker

| 用途 | コマンド |
|------|---------|
| 開発（ホットリロード） | `venv\Scripts\python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000` |
| 本番同等 | `docker compose up --build` |
