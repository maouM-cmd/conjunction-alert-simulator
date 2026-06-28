# CAS v1.0.0 — Phase 4 complete

**Conjunction Alert Simulator** の初回安定版です。TLE からデブリ接近を検出し、Pc 計算・CDM 比較・コンステレーション監視・Docker デプロイまでをカバーします。

## ハイライト

- **接近検出** — SGP4 伝播 + 高度プレフィルタ + 7 日間スキャン
- **Pc** — Foster（デフォルト）、Alfriend encounter plane（opt-in）、TLE RTN 非等方共分散
- **CDM** — インポート比較、Space-Track アラート取得、KVN エクスポート
- **運用** — Webhook 通知スタブ、batch 25 衛星並列
- **デプロイ** — `docker compose up` ワンコマンド

## デモ

![Demo](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/demo.gif)

## クイックスタート

```powershell
git clone https://github.com/maouM-cmd/conjunction-alert-simulator.git
cd conjunction-alert-simulator
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

→ http://127.0.0.1:8000/app/ — **デモ TLE 読込** → **接近解析**

Docker: `docker compose up --build -d`

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [API 設計](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/api-design.md)
- [デプロイ](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/deploy.md)
- [CHANGELOG](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/CHANGELOG.md)

**License:** MIT
