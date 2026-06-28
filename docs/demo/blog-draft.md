# Conjunction Alert Simulator を作った — 軌道力学と衝突回避の縮小版

**公開リポ:** https://github.com/maouM-cmd/conjunction-alert-simulator

**Live Demo:** https://conjunction-alert-simulator.onrender.com/app/

**Zenn 版:** https://zenn.dev/hukuhukuchan/articles/6bd364012c6bf5

低軌道衛星と宇宙デブリの接近（Conjunction）は、大規模コンステレーション運用では毎日の課題です。本番システムは Space-Track、CDM、Pc 計算、通知連携を含みますが、CAS では **TLE + SGP4 + REST + Cesium** でその流れを OSS として再現しました。

![Demo](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/demo.gif)

## できること

- 7 日間デブリ接近検出（CelesTrak / Space-Track）
- **Pc** — Foster（デフォルト）、Alfriend encounter plane（opt-in）、TLE RTN 非等方 / **CDM σ on 一覧**
- **CDM 比較** — Foster / Alfriend / Monte Carlo 並列
- **Space-Track CDM アラート** — 認証設定時のみ
- **Batch** — 最大 25 衛星、ProcessPool 並列
- **Docker / クラウド** — Render / Fly.io manifest（Phase 5B）
- **Webhook** — generic JSON / **Slack Incoming Webhook**（Phase 5C）
- CesiumJS 3D + 回避マニューバ試算

![接近一覧 Advanced Pc](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/02-conjunctions.png)

## Phase 5 で追加したこと

### 5B — クラウドデプロイ

- フロント API **同一オリジン**（クラウド URL から `/app/` だけで動作）
- **Live Demo（Phase 6C）:** https://conjunction-alert-simulator.onrender.com/app/

### 5C — 運用連携

- `ALERT_WEBHOOK_FORMAT=slack` で Slack 通知
- `cdm_text` + `apply_cdm_covariance` で接近一覧に CDM encounter σ を opt-in 適用

## Phase 6 — ポートフォリオ公開

- **6A:** GitHub Release v1.1.0、Zenn 投稿、公開チェックリスト
- **6B:** GitHub Actions `deploy.yml` — pytest → Render Hook → `verify_deploy`
- **6C:** Render Live Demo 稼働

## Pc の段階的実装

1. **Foster 2D** — TLE 経過日数から σ 推定
2. **Encounter plane** — CDM RTN 共分散を encounter 2×2 に射影、Alfriend 積分
3. **一覧 advanced Pc** — `use_advanced_pc=true`
4. **CDM σ on 一覧** — 共分散付き CDM KVN を `/conjunctions` に渡して Pc 上書き

![CDM vs CAS 比較](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/05-cdm-compare.png)

## 2 分デモ

### クラウド（推奨）

→ **https://conjunction-alert-simulator.onrender.com/app/**

1. cold start 後 **デモ TLE 読込** → **高精度 Pc** ON → 閾値 50 km → **接近解析**

### ローカル

```powershell
git clone https://github.com/maouM-cmd/conjunction-alert-simulator.git
cd conjunction-alert-simulator
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

→ http://127.0.0.1:8000/app/

## まとめ

CAS は Starlink 型の接近監視フローを学習・ポートフォリオ用に縮小したツールです。**v1.1.1** で Phase 6（公開・Live Demo・CI/CD）が揃いました。

- リポ: https://github.com/maouM-cmd/conjunction-alert-simulator
- Live Demo: https://conjunction-alert-simulator.onrender.com/app/
- Zenn: https://zenn.dev/hukuhukuchan/articles/6bd364012c6bf5
- Release: https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.1.1

MIT License。フィードバックは [GitHub Issues](https://github.com/maouM-cmd/conjunction-alert-simulator/issues) へ。
