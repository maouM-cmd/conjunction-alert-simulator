# Conjunction Alert Simulator (CAS)

[![GitHub](https://img.shields.io/badge/GitHub-maouM--cmd%2Fconjunction--alert--simulator-blue)](https://github.com/maouM-cmd/conjunction-alert-simulator)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![tests](https://github.com/maouM-cmd/conjunction-alert-simulator/actions/workflows/test.yml/badge.svg)](https://github.com/maouM-cmd/conjunction-alert-simulator/actions/workflows/test.yml)
[![deploy](https://github.com/maouM-cmd/conjunction-alert-simulator/actions/workflows/deploy.yml/badge.svg)](https://github.com/maouM-cmd/conjunction-alert-simulator/actions/workflows/deploy.yml)
[![Release](https://img.shields.io/github/v/release/maouM-cmd/conjunction-alert-simulator)](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.1.1)

![Demo](docs/demo/demo.gif)

衛星の TLE を入力すると、今後7日間に接近する宇宙デブリを検出し、3D で軌道と最接近点（TCA）を表示し、回避マニューバの効果を試算する Web アプリです。

**v1.1.0（Phase 5）** — Render/Fly クラウド manifest、Slack Webhook、CDM σ on 接近一覧、Advanced Pc デモ素材を追加。Starlink 型の接近監視フローを OSS で再現したポートフォリオ作品です。

## 2 分デモ（ローカル）

```powershell
git clone https://github.com/maouM-cmd/conjunction-alert-simulator.git
cd conjunction-alert-simulator
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

1. ブラウザで **http://127.0.0.1:8000/app/** を開く
2. **デモ TLE 読込** → **高精度 Pc** ON → **接近解析**（閾値 50 km）
3. イベントを選択 → 3D 表示 → 回避試算

Docker 代替: `docker compose up --build -d` → http://localhost:8000/app/

## Live Demo

[![Live Demo](https://img.shields.io/badge/Live_Demo-Render-46E3B7)](https://conjunction-alert-simulator.onrender.com/app/)

**https://conjunction-alert-simulator.onrender.com/app/** — Render Free tier（API 同一オリジン）。cold start 後 **デモ TLE 読込 → 高精度 Pc ON → 接近解析**（閾値 50 km）。

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/maouM-cmd/conjunction-alert-simulator)

再デプロイ手順: [docs/deploy-render-phase6c.md](docs/deploy-render-phase6c.md) | CI/CD: [docs/deploy-render-cicd.md](docs/deploy-render-cicd.md) | URL 正本: [docs/LIVE_DEMO_URL.md](docs/LIVE_DEMO_URL.md)

| 方法 | 手順 |
|------|------|
| Render（稼働中） | [deploy-render-phase6c.md](docs/deploy-render-phase6c.md) — [`render.yaml`](render.yaml) Blueprint |
| Fly.io | [deploy-cloud.md](docs/deploy-cloud.md#flyio) — [`fly.toml`](fly.toml) |

## 機能

- 自衛星 TLE 入力 → デブリ接近イベント一覧（閾値可変）
- **衝突確率 Pc** — Foster 2D（一覧デフォルト）、opt-in で **Alfriend encounter plane** + **TLE RTN 非等方共分散**
- **Webhook 通知** — 高リスクイベントを Webhook へ POST（generic / Slack Incoming Webhook）
- **CDM σ on 一覧** — `cdm_text` + `apply_cdm_covariance` で接近一覧 Pc に CDM 共分散適用
- **CDM インポート** — RTN 共分散の encounter plane 射影、外部 Pc vs CAS 3方式比較
- **Space-Track CDM アラート** — `cdm_public` 取得、一覧比較、CAS から CDM KVN エクスポート
- **コンステレーション監視** — 最大 25 衛星の TLE 一括接近解析（ProcessPool 並列）
- CesiumJS による 3D 軌道可視化・TCA マーカー・タイムスライダー
- prograde / retrograde / normal 方向の Δv 試算（Before/After）

## 技術スタック

- **Backend:** Python 3.12, FastAPI, SGP4
- **Frontend:** HTML + CesiumJS（ビルド不要）
- **データ:** [CelesTrak](https://celestrak.org/)（デフォルト）/ [Space-Track](https://www.space-track.org/)（オプション）

## Space-Track 連携（オプション）

1. [Space-Track](https://www.space-track.org/auth/createAccount) でアカウント作成
2. `.env.example` を `.env` にコピーして認証情報を設定

```powershell
copy .env.example .env
# SPACE_TRACK_USER / SPACE_TRACK_PASSWORD を編集
# TLE_PROVIDER=spacetrack
```

未設定時は CelesTrak のみ使用。Space-Track 失敗時は CelesTrak に自動フォールバック。

## セットアップ

```powershell
cd C:\Users\admin\OneDrive\ドキュメント\conjunction-alert-simulator
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

## 起動

```powershell
# API サーバ（プロジェクトルートから）
venv\Scripts\python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# 別ターミナルで静的フロント（任意）
cd frontend
python -m http.server 8080
```

ブラウザで `http://127.0.0.1:8080` を開く（API は `http://127.0.0.1:8000`）。

FastAPI 経由でフロントも配信する場合は `http://127.0.0.1:8000/app/` を開いてください。

## Docker で起動（Phase 4C）

```powershell
copy .env.example .env   # 任意（Space-Track 利用時は編集）
docker compose up --build -d
```

- UI: **http://localhost:8000/app/**
- ヘルス: `curl http://localhost:8000/health`

詳細は [docs/deploy.md](docs/deploy.md) を参照。

## Webhook 通知（任意）

`.env` に以下を設定:

```env
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
ALERT_WEBHOOK_FORMAT=slack
ALERT_PC_THRESHOLD=0.00001
```

解析リクエストで `notify_webhook: true` を指定するか、UI の **Webhook テスト** / `POST /api/v1/alerts/webhook/test` で接続確認。batch 解析でも `notify_webhook` 対応（fleet 一括 POST）。

## CLI（軌道伝播プロトタイプ）

```powershell
venv\Scripts\python -m backend.cli.propagate --tle1 samples/iss.tle --tle2 samples/debris-sample.tle
```

## API 概要

| エンドポイント | メソッド | 概要 |
|---------------|---------|------|
| `/health` | GET | 死活監視 |
| `/api/v1/conjunctions` | POST | 接近イベント検出 |
| `/api/v1/conjunctions/batch` | POST | 複数衛星一括接近解析 |
| `/api/v1/alerts/webhook/test` | POST | Webhook 接続テスト |
| `/api/v1/cdm/parse` | POST | CDM テキスト解析 |
| `/api/v1/cdm/compare` | POST | CDM vs CAS 比較 |
| `/api/v1/cdm/fetch` | POST | Space-Track CDM アラート取得 |
| `/api/v1/cdm/compare-alert` | POST | CDM アラート + TLE 自動比較 |
| `/api/v1/cdm/export` | POST | 接近イベント → CDM KVN |
| `/api/v1/orbit` | POST | 軌道点列（3D 表示用） |
| `/api/v1/maneuver/preview` | POST | 回避マニューバ試算 |

詳細は [docs/api-design.md](docs/api-design.md) を参照。

## ドキュメント

- [要件定義書 Phase 6A](docs/requirements-phase6a.md)
- [要件定義書 Phase 6C](docs/requirements-phase6c.md)
- [要件定義書 Phase 6B](docs/requirements-phase6b.md)
- [Render CI/CD Phase 6B](docs/deploy-render-cicd.md)
- [Render デプロイ Phase 6C](docs/deploy-render-phase6c.md)
- [Live Demo URL](docs/LIVE_DEMO_URL.md)
- [GitHub Release 手順](docs/publish-github-release.md)
- [要件定義書 Phase 6E](docs/requirements-phase6e.md)
- [Qiita 投稿手順](docs/publish-qiita.md)
- [GitHub Social Preview](docs/publish-github-social-preview.md)
- [要件定義書 Phase 1](docs/requirements.md)
- [要件定義書 Phase 2](docs/requirements-phase2.md)
- [要件定義書 Phase 3](docs/requirements-phase3.md)
- [要件定義書 Phase 3.5](docs/requirements-phase35.md)
- [要件定義書 Phase 4A](docs/requirements-phase4a.md)
- [要件定義書 Phase 4A-Ext](docs/requirements-phase4a-ext.md)
- [要件定義書 Phase 4B](docs/requirements-phase4b.md)
- [要件定義書 Phase 4B-Ext](docs/requirements-phase4b-ext.md)
- [要件定義書 Phase 4C](docs/requirements-phase4c.md)
- [要件定義書 Phase 4D](docs/requirements-phase4d.md)
- [要件定義書 Phase 5A](docs/requirements-phase5a.md)
- [要件定義書 Phase 5B](docs/requirements-phase5b.md)
- [要件定義書 Phase 5C](docs/requirements-phase5c.md)
- [要件定義書 Phase 5D](docs/requirements-phase5d.md)
- [クラウドデプロイ](docs/deploy-cloud.md)
- [Zenn 投稿手順](docs/publish-zenn.md)
- [GitHub About 設定](docs/publish-github-about.md)
- [公開チェックリスト v1.1.0](docs/publish-checklist-v1.1.0.md)
- [CHANGELOG](CHANGELOG.md)
- [デプロイ手順](docs/deploy.md)
- [API 設計書](docs/api-design.md)
- [アーキテクチャ](docs/architecture.md)

## ライセンス

MIT License — 詳細は [LICENSE](LICENSE)

## 技術記事

| | |
|--|--|
| Live Demo | [conjunction-alert-simulator.onrender.com/app/](https://conjunction-alert-simulator.onrender.com/app/) |
| Zenn | [Conjunction Alert Simulator を作った](https://zenn.dev/hukuhukuchan/articles/6bd364012c6bf5) |
| Release | [v1.1.1 — Phase 6 portfolio](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.1.1) |
| Qiita | 準備中 — 原稿 [`docs/demo/blog-draft.md`](docs/demo/blog-draft.md) / [`docs/publish-qiita.md`](docs/publish-qiita.md) |
| Social Preview | [`docs/publish-github-social-preview.md`](docs/publish-github-social-preview.md) |
| 公開チェックリスト | [`docs/publish-checklist-v1.1.0.md`](docs/publish-checklist-v1.1.0.md) |
| GitHub About | [`docs/publish-github-about.md`](docs/publish-github-about.md) |

## デモ

| | |
|--|--|
| 初期画面 | ![01](docs/demo/01-initial.png) |
| 接近一覧（Advanced Pc） | ![02](docs/demo/02-conjunctions.png) |
| 3D 軌道 | ![03](docs/demo/03-orbit-tca.png) |
| 回避試算 | ![04](docs/demo/04-maneuver.png) |
| CDM 比較 | ![05](docs/demo/05-cdm-compare.png) |

**UI デモ:** 「デモ TLE 読込」→ **高精度 Pc** ON → 接近解析（閾値 50 km）→ イベント選択 → 3D 表示 → 試算実行

手順: [docs/demo/README.md](docs/demo/README.md) | 技術ブログ: [docs/demo/blog-zenn.md](docs/demo/blog-zenn.md) | Zenn 投稿: [docs/publish-zenn.md](docs/publish-zenn.md)

