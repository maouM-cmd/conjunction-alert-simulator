# Changelog

All notable changes to Conjunction Alert Simulator (CAS) are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.2.1] - 2026-06-28

Phase 8 — Space-Track CDM 自動マージ（単一衛星 + batch）。

### Added

- **Phase 8A:** `auto_spacetrack_cdm` on `/conjunctions`、`spacetrack_cdm_*` レスポンスメタ、UI チェックボックス
- **Phase 8A-ext:** batch `/conjunctions/batch` 同機能、`BatchSummaryOut` fleet CDM 集計

## [1.2.0] - 2026-06-28

Phase 7 機能拡張 — 高度プリフィルタ UX、Space-Track CDM RTN 共分散、Slack Bot 通知。

### Added

- **Phase 7C:** `use_altitude_prefilter` on `/conjunctions` and batch、`debris_candidates_count`、Live Demo cold start `/health` ポーリング / `apiPost` リトライ
- **Phase 7A:** Space-Track CDM RTN 共分散パース、`fetch_cdm_detail` lazy 取得、compare-alert `sigma_source: cdm_covariance`、`has_rtn_covariance` UI バッジ
- **Phase 7B:** `ALERT_WEBHOOK_FORMAT=slack_bot`（`SLACK_BOT_TOKEN` + `SLACK_CHANNEL_ID`）、`/health` `alert_delivery_*`

## [1.1.1] - 2026-06-28

Phase 6 ポートフォリオ完結 — Live Demo、Zenn 公開、Render CI/CD、仕上げドキュメント。

### Added

- **Phase 6A:** 公開チェックリスト、GitHub Release v1.1.0、Zenn 原稿・投稿手順
- **Phase 6C:** Render Live Demo URL、verify_deploy CLI、deploy-render-phase6c.md
- **Phase 6B:** GitHub Actions deploy.yml（pytest → Render Hook → verify_deploy）
- **Phase 6E:** Qiita 原稿、Social Preview 素材、CI pytest 一本化、v1.1.1 release notes

## [1.1.0] - 2026-06-28

Phase 5 リリース — クラウド manifest、運用 Webhook、CDM σ 一覧、デモ刷新。

### Added

- **Phase 5B:** 同一オリジン API、Render/Fly manifest、`docs/deploy-cloud.md`、動的 `PORT`
- **Phase 5C:** Slack Incoming Webhook（`ALERT_WEBHOOK_FORMAT=slack`）、`cdm_text` + `apply_cdm_covariance` on `/conjunctions`、batch Webhook + UI テスト
- **Phase 5D:** `find_demo_pair` Advanced Pc メタ、Phase 5 デモ PNG/GIF、Zenn 原稿更新

## [1.0.0] - 2026-06-28

Phase 4 完成リリース — 接近監視から Pc / CDM 運用連携 / Docker まで一気通貫。

### Added

- **Phase 1:** TLE 入力 → デブリ接近検出、CesiumJS 3D 可視化、回避マニューバ試算
- **Phase 2:** Foster 2D 衝突確率 Pc、Space-Track TLE 連携（CelesTrak フォールバック）
- **Phase 3:** CDM インポート・比較 UI、コンステレーション batch API（最大 25 衛星）
- **Phase 3.5:** CDM RTN 共分散 encounter 射影、batch ProcessPool 並列化
- **Phase 4A:** Alfriend encounter plane Pc、Monte Carlo（CDM 比較）
- **Phase 4A-Ext:** 一覧 `/conjunctions` に `use_advanced_pc` opt-in
- **Phase 4B:** Space-Track `cdm_public` 取得、CDM アラート UI、CDM KVN エクスポート
- **Phase 4B-Ext:** TLE RTN 非等方共分散、Webhook 通知スタブ
- **Phase 4C:** Dockerfile / docker-compose、デプロイ手順
- **Phase 4D:** デモ PNG/GIF、技術ブログ Phase 4 版、ポートフォリオ素材

### Changed

- 接近イベント一覧は Pc 降順ソート（Phase 2 以降）
- リスクレベルは Pc 優先判定（high ≥ 10⁻⁴、medium ≥ 10⁻⁶）

[1.2.1]: https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.2.1
[1.2.0]: https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.2.0
[1.1.1]: https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.1.1
[1.1.0]: https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.1.0
[1.0.0]: https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.0.0
