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

生成物: `01-initial.png` 〜 `05-cdm-compare.png`, `demo.gif`, `assets-meta.json`

## デモ TLE の再生成

ISS ベースで **Advanced Pc 降順** top イベントのペアを探索:

```powershell
venv\Scripts\python -m backend.cli.find_demo_pair --satellite samples/iss.tle
```

出力:

- `samples/demo-satellite.tle`, `demo-debris.tle`
- `samples/demo-pair.json` — `pc`, `pc_alfriend`, `pc_method_used`, `miss_distance_km`, `tca` 等
- `samples/example.cdm` — TCA / miss / Pc を demo-pair と同期

## UI デモ手順（Phase 5）

1. `http://127.0.0.1:8000/app/` を開く
2. **デモ TLE 読込**（閾値 50 km）
3. **高精度 Pc** ON → 任意で **非等方 RTN 共分散** ON
4. **CDM 共分散（任意）** — `example.cdm` 貼付 + **CDM 共分散を Pc に適用** ON
5. **接近解析** → イベント選択 → 3D 表示 → **試算実行**
6. **Webhook テスト** — `.env` に `ALERT_WEBHOOK_URL` 設定時
7. **CDM 比較** タブ — デモ CDM 読込 → 比較 → **単一衛星解析へ**
8. **CDM アラート** タブ — Space-Track `.env` 設定時のみ

## Docker デモ

```powershell
docker compose up --build -d
```

→ http://localhost:8000/app/

## Webhook テスト（任意）

`.env` に `ALERT_WEBHOOK_URL` / `ALERT_WEBHOOK_FORMAT=slack` を設定後:

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/alerts/webhook/test
```

または UI の **Webhook テスト** ボタン。

## 手動キャプチャ（任意）

ブラウザ録画: Xbox Game Bar（Win+G）で 30〜60 秒録画し `demo.gif` に保存。

## 注意

- 初回は CelesTrak からデブリカタログを取得するためネットワークが必要
- キャッシュは `data/cache/` に 24 時間保持
- Space-Track CDM アラートは認証なしでは 503
- 一覧 top の Pc が小さい場合も **CDM 比較**で Pc デモ可能（`example.cdm`）
