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

## PaaS デプロイ（参考）

実際のデプロイはユーザー環境で実施。共通手順:

1. リポジトリを GitHub に push（済み）
2. Render / Fly.io 等で **Dockerfile** デプロイを選択
3. 環境変数に Space-Track 認証を設定（任意）
4. 永続ディスクを `/app/data/cache` にマウント（TLE キャッシュ推奨）
5. 公開 URL の `/app/` をブックマーク

HTTPS は各 PaaS の自動 TLS を利用。

---

## 開発 vs Docker

| 用途 | コマンド |
|------|---------|
| 開発（ホットリロード） | `venv\Scripts\python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000` |
| 本番同等 | `docker compose up --build` |
