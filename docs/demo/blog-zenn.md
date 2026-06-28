---
title: Conjunction Alert Simulator を作った — 軌道力学と衝突回避の縮小版
emoji: 🛰️
type: tech
topics: [Python, FastAPI, 宇宙, OSS, Docker, SGP4]
published: false
---

# Conjunction Alert Simulator を作った — 軌道力学と衝突回避の縮小版

**公開リポ:** https://github.com/maouM-cmd/conjunction-alert-simulator

低軌道衛星と宇宙デブリの接近（Conjunction）は、大規模コンステレーション運用では毎日の課題です。本番システムは Space-Track、CDM、Pc 計算、通知連携を含みますが、CAS では **TLE + SGP4 + REST + Cesium** でその流れを OSS として再現しました。

![Demo](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/demo.gif)

## できること

- 7 日間デブリ接近検出（CelesTrak / Space-Track）
- **Pc** — Foster（デフォルト）、Alfriend encounter plane（opt-in）、TLE RTN 非等方共分散
- **CDM 比較** — Foster / Alfriend / Monte Carlo 並列
- **Space-Track CDM アラート** — 認証設定時のみ
- **Batch** — 最大 25 衛星、ProcessPool 並列
- **Docker** — `docker compose up`
- **Webhook** — 高リスクイベント POST スタブ
- CesiumJS 3D + 回避マニューバ試算

![接近一覧 Advanced Pc](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/02-conjunctions.png)

## 技術スタック

| レイヤ | 選定 |
|--------|------|
| 軌道伝播 | SGP4（`sgp4`） |
| API | FastAPI + Pydantic |
| 3D | CesiumJS |
| データ | CelesTrak / Space-Track（24h キャッシュ） |
| デプロイ | Docker / docker-compose |

## Pc の段階的実装

1. **Foster 2D** — TLE 経過日数から σ 推定
2. **Encounter plane** — CDM RTN 共分散を TEME → encounter 2×2 に射影、Alfriend 積分
3. **一覧 advanced Pc** — `use_advanced_pc=true` で Alfriend を primary に
4. **TLE 非等方** — RTN 対角（径方向 σ を大きく）で encounter 共分散を構築

![CDM vs CAS 比較](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/05-cdm-compare.png)

## 性能

デブリ数千件 × 7 日 × 1 分刻みは重いため、**高度 ±200 km プレフィルタ** と batch **ProcessPool** を実装。

## 2 分デモ

```powershell
git clone https://github.com/maouM-cmd/conjunction-alert-simulator.git
cd conjunction-alert-simulator
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

→ http://127.0.0.1:8000/app/ （**デモ TLE 読込** → **高精度 Pc** ON → 閾値 50 km → **接近解析**）

## Docker

```powershell
docker compose up --build -d
```

→ http://localhost:8000/app/

## Webhook（任意）

```env
ALERT_WEBHOOK_URL=https://example.com/hook
ALERT_PC_THRESHOLD=0.00001
```

`POST /api/v1/alerts/webhook/test` で ping。

## まとめ

CAS は Starlink 型の接近監視フローを学習・ポートフォリオ用に縮小したツールです。**v1.0.0** で Phase 4 機能が一通り揃いました。

- リポ: https://github.com/maouM-cmd/conjunction-alert-simulator
- Release: https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.0.0

MIT License。フィードバックは [GitHub Issues](https://github.com/maouM-cmd/conjunction-alert-simulator/issues) へ。
