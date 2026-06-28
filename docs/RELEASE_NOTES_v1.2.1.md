# CAS v1.2.1 — Phase 8 CDM auto-merge

**Conjunction Alert Simulator** v1.2.1 — Space-Track CDM 自動マージ（単一衛星 + batch）。

## ハイライト

- **Phase 8A** — `auto_spacetrack_cdm` on `/conjunctions`：手動 CDM ペーストなしで接近一覧に RTN 共分散 Pc（`sigma_source: cdm_covariance`）
- **Phase 8A-ext** — batch `/conjunctions/batch` 同機能 + fleet サマリ（`spacetrack_cdm_events_merged`）

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| Zenn | https://zenn.dev/hukuhukuchan/articles/6bd364012c6bf5 |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 8 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase8a.md |

## デモ

![Demo](https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/demo.gif)

Space-Track 認証あり（`.env`）:

1. **単一衛星** — **Space-Track CDM 自動適用** ON → **高精度 Pc** ON → **接近解析**
2. **コンステレーション** — 同チェック ON → **一括解析** → サマリにマージ件数

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [CHANGELOG](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/CHANGELOG.md)
- [v1.2.0 — Phase 7](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.2.0)

**License:** MIT
