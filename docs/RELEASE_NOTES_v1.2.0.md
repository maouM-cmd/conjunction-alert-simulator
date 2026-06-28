# CAS v1.2.0 — Phase 7 feature release

**Conjunction Alert Simulator** v1.2.0 — Phase 7 機能拡張（性能 UX、CDM RTN 共分散、Slack Bot 通知）。

## ハイライト

- **Phase 7C** — 高度帯プリフィルタ API/UI、`debris_candidates_count`、Live Demo cold start ポーリング / API リトライ
- **Phase 7A** — Space-Track CDM RTN 共分散パース、`fetch_cdm_detail`、compare-alert で `sigma_source: cdm_covariance`、RTN σ UI バッジ
- **Phase 7B** — `ALERT_WEBHOOK_FORMAT=slack_bot` + Slack `chat.postMessage`、`/health` で配信モード表示

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| Zenn | https://zenn.dev/hukuhukuchan/articles/6bd364012c6bf5 |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 7 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase7.md |

## デモ

![Demo](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/demo.gif)

クラウド: **https://conjunction-alert-simulator.onrender.com/app/** — **デモ TLE 読込** → **高精度 Pc** ON → **接近解析**

Space-Track 認証あり: **CDM アラート** タブで RTN σ 付き compare-alert を試せます。

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [Phase 7A — CDM RTN](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase7a.md)
- [Phase 7B — Slack Bot](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase7b.md)
- [CHANGELOG](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/CHANGELOG.md)

**License:** MIT
