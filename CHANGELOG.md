# Changelog

All notable changes to Conjunction Alert Simulator (CAS) are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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

[1.1.0]: https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.1.0
[1.0.0]: https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.0.0
