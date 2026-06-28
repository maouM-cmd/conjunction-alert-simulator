# Conjunction Alert Simulator を作った — 軌道力学と衝突回避の縮小版

**公開リポ:** https://github.com/maouM-cmd/conjunction-alert-simulator

## はじめに

低軌道（LEO）衛星の数は増え続け、宇宙デブリとの接近（Conjunction）は日常の運用課題になっています。本番の衝突回避システムは Space-Track 認証、CDM（Conjunction Data Message）、衝突確率 Pc、Webhook 通知などを組み合わせます。

OSS として公開した **Conjunction Alert Simulator（CAS）** は、その流れを **TLE + SGP4 + FastAPI + CesiumJS** で縮小再現したポートフォリオ向けツールです。

![Demo](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/demo.gif)

## 何ができるか（Phase 4 完成版）

1. 自衛星 TLE 入力（**デモ TLE 読込** ボタン付き）
2. CelesTrak / Space-Track デブリカタログと 7 日間・1 分刻み SGP4 伝播
3. 接近イベント一覧 — Foster Pc（デフォルト）または **Alfriend encounter plane Pc**（opt-in）
4. **TLE RTN 非等方共分散** — advanced Pc 時に opt-in
5. CesiumJS 3D 可視化 + prograde / retrograde / normal Δv 試算
6. **CDM 比較** — 外部 Pc vs CAS（Foster / Alfriend / Monte Carlo）
7. **Space-Track CDM アラート** — `cdm_public` 取得 → CAS 比較（`.env` 認証時）
8. **コンステレーション batch** — 最大 25 衛星、ProcessPool 並列
9. **Docker** — `docker compose up` でワンコマンド起動
10. **Webhook 通知スタブ** — 高リスクイベントを汎用 URL へ POST

## Pc 計算の進化

| フェーズ | 内容 |
|---------|------|
| Phase 2 | Foster 2D（距離 + σ 推定） |
| Phase 4A | CDM RTN 共分散 → encounter plane → Alfriend / MC |
| Phase 4A-Ext | 一覧 API に advanced Pc opt-in |
| Phase 4B-Ext | TLE 由来 RTN 非等方共分散（R×2, T/N×0.5） |

リスクレベルは Pc 優先: high ≥ 10⁻⁴、medium ≥ 10⁻⁶。

## アーキテクチャ

```
Frontend (CesiumJS)  ←→  FastAPI  ←→  Services
                              ├── tle_fetcher / spacetrack_client
                              ├── propagator (SGP4 / TEME)
                              ├── conjunction + analysis (高度プレフィルタ)
                              ├── pc_conjunction + tle_rtn_covariance
                              ├── cdm_* (parse, compare, export, fetch)
                              └── webhook_notifier
```

## デモ用 TLE

ISS サンプルは 5 km 閾値で接近 0 件になりがちです。`backend/cli/find_demo_pair.py` でカタログから最接近デブリを探索し `samples/demo-*.tle` を生成（例: ISS vs COSMOS 2251 DEB、約 30 km）。

## 使ってみる

### ローカル

```powershell
git clone https://github.com/maouM-cmd/conjunction-alert-simulator.git
cd conjunction-alert-simulator
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

`http://127.0.0.1:8000/app/` → **デモ TLE 読込** → **高精度 Pc** ON → **接近解析**（閾値 50 km）

### Docker

```powershell
docker compose up --build -d
```

詳細: [docs/deploy.md](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/deploy.md)

### Webhook（任意）

`.env` に `ALERT_WEBHOOK_URL=https://...` を設定し、`POST /api/v1/alerts/webhook/test` で接続確認。

## スクリーンショット

| | |
|--|--|
| タイトル | ![01](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/01-initial.png) |
| 接近一覧（Advanced Pc） | ![02](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/02-conjunctions.png) |
| 軌道 | ![03](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/03-orbit-tca.png) |
| 回避試算 | ![04](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/04-maneuver.png) |
| CDM 比較 | ![05](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/05-cdm-compare.png) |

## まとめ

CAS は Starlink 型の接近監視フローを学習・ポートフォリオ用に縮小したツールです。**v1.0.0** で Phase 4 機能が一通り揃いました。

- Release: https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.0.0

**ライセンス:** MIT
