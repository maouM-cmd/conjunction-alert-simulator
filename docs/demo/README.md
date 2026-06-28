# デモ手順

Conjunction Alert Simulator（CAS）のデモ用スクリーンショット・GIF です。

## 自動生成（推奨）

```powershell
cd C:\Users\admin\OneDrive\ドキュメント\conjunction-alert-simulator
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
# 別ターミナル
venv\Scripts\python -m backend.cli.generate_demo_assets
```

生成物: `01-initial.png` 〜 `05-cdm-compare.png`, `demo.gif`

## デモ TLE の再生成

ISS に最も近いデブリペアを探索:

```powershell
venv\Scripts\python -m backend.cli.find_demo_pair
```

出力: `samples/demo-satellite.tle`, `samples/demo-debris.tle`, `demo-pair.json`

## UI デモ手順（Phase 4）

1. `http://127.0.0.1:8000/app/` を開く
2. **デモ TLE 読込**（閾値 50 km）
3. **高精度 Pc** ON → 任意で **非等方 RTN 共分散** ON
4. **接近解析** → イベント選択 → 3D 表示 → **試算実行**
5. **CDM 比較** タブ — デモ CDM 読込 → 比較実行
6. **CDM アラート** タブ — Space-Track `.env` 設定時のみ

## Docker デモ

```powershell
docker compose up --build -d
```

→ http://localhost:8000/app/

## Webhook テスト（任意）

`.env` に `ALERT_WEBHOOK_URL` を設定後:

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/alerts/webhook/test
```

## 手動キャプチャ（任意）

ブラウザ録画: Xbox Game Bar（Win+G）で 30〜60 秒録画し `demo.gif` に保存。

## 注意

- 初回は CelesTrak からデブリカタログを取得するためネットワークが必要
- キャッシュは `data/cache/` に 24 時間保持
- Space-Track CDM アラートは認証なしでは 503
