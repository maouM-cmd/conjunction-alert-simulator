# CAS クラウドデプロイ手順

**対象:** Phase 5B — Render / Fly.io

ローカル Docker 手順は [deploy.md](deploy.md) を参照。

---

## 共通前提

- GitHub リポジトリ: https://github.com/maouM-cmd/conjunction-alert-simulator
- フロントは FastAPI から `/app/` 配信 — API は**同一オリジン**（`frontend/js/app.js`）
- TLE キャッシュ: コンテナ内 `/app/data/cache`（永続ディスク推奨）
- 初回接近解析は CelesTrak 取得のため **30〜90 秒**かかることがある

### 推奨デモ設定

| 項目 | 推奨値 |
|------|--------|
| 閾値 | 50 km |
| duration_days | 7 |
| step_minutes | 1 |
| use_advanced_pc | UI で ON（任意） |

Free tier ではスリープ復帰後も同様に初回が遅くなります。504 回避のため閾値を広げすぎないでください。

---

## Render

### 1. Blueprint（推奨）

1. [Render Dashboard](https://dashboard.render.com/) → **New** → **Blueprint**
2. GitHub リポ `maouM-cmd/conjunction-alert-simulator` を接続
3. ルートの [`render.yaml`](../render.yaml) を読み込んでデプロイ

または README の Deploy to Render リンクから開始。

### 2. 手動 Web Service

1. **New Web Service** → Docker
2. Dockerfile パス: `./Dockerfile`
3. **Health Check Path:** `/health`
4. **Disk:** Mount `/app/data/cache`（1 GB 以上推奨）
5. 環境変数（任意）:
   - `SPACE_TRACK_USER` / `SPACE_TRACK_PASSWORD`
   - `TLE_PROVIDER=spacetrack`
   - `ALERT_WEBHOOK_URL`
   - `BATCH_MAX_WORKERS=2`

### 3. 確認

```bash
curl https://<your-service>.onrender.com/health
```

ブラウザ: `https://<your-service>.onrender.com/app/`

### Render Free tier 注意

- 非アクセス時スリープ → 初回アクセスで cold start（数十秒）
- 永続ディスクはプランにより制限あり（Starter 以上を推奨する場合あり）

---

## Fly.io

### 1. 初回セットアップ

```powershell
# flyctl インストール: https://fly.io/docs/hands-on/install-flyctl/
fly auth login
cd conjunction-alert-simulator
fly launch
```

- `fly.toml` の `app = "cas-demo"` を一意の名前に変更
- リージョン例: `nrt`（東京近傍）

### 2. 永続ボリューム

```powershell
fly volumes create cas_cache --region nrt --size 1
fly deploy
```

[`fly.toml`](../fly.toml) の `[mounts]` で `/app/data/cache` にマウント済み。

### 3. 環境変数（任意）

```powershell
fly secrets set SPACE_TRACK_USER=xxx SPACE_TRACK_PASSWORD=yyy
fly secrets set ALERT_WEBHOOK_URL=https://example.com/hook
```

### 4. 確認

```powershell
fly open /app/
curl https://<your-app>.fly.dev/health
```

---

## デプロイ後

1. README の **Live Demo** URL を更新
2. **デモ TLE 読込** → **接近解析** で動作確認
3. Space-Track CDM は `.env` / secrets 設定時のみ

---

## トラブルシュート

| 症状 | 対処 |
|------|------|
| UI は開くが API 失敗 | 同一ホストの `/app/` から開いているか確認（8080 静的サーバ単体は不可） |
| 504 タイムアウト | 閾値を 50 km 程度に、cold start 後に再試行 |
| キャッシュが毎回空 | 永続ディスク / Fly volume がマウントされているか確認 |
| `/cdm/fetch` 503 | Space-Track 認証未設定（正常） |
