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

生成物: `docs/demo/01-initial.png` 〜 `04-maneuver.png`, `demo.gif`

## デモ TLE の再生成

ISS に最も近いデブリペアを探索:

```powershell
venv\Scripts\python -m backend.cli.find_demo_pair
```

出力: `samples/demo-satellite.tle`, `samples/demo-debris.tle`, `demo-pair.json`

## UI デモ手順

1. `http://127.0.0.1:8000/app/` を開く
2. **デモ TLE 読込** をクリック（閾値 50 km が自動設定）
3. **接近解析** → イベント一覧から1件選択 → 3D 表示 → **試算実行**

## 手動キャプチャ（任意）

ブラウザ録画: Xbox Game Bar（Win+G）で 30〜60 秒録画し `docs/demo/demo.gif` に保存。

## 注意

- 初回は CelesTrak からデブリカタログを取得するためネットワークが必要
- キャッシュは `data/cache/` に 24 時間保持
