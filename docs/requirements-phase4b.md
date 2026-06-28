# CAS Phase 4B — 要件定義書

**版:** 4B  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase4b.md`）

---

## 1. 概要

Phase 4B では Space-Track **cdm_public** から接近 CDM を取得し、アラート UI と CAS 比較・CDM エクスポートにより運用連携フローを実現する。

| サブフェーズ | 内容 |
|-------------|------|
| 4B-1 | Space-Track CDM 取得 API |
| 4B-2 | CDM アラート UI + compare-alert |
| 4B-3 | 接近イベント → CDM KVN エクスポート |
| 4B-4 | ドキュメント + テスト + ship |

---

## 2. 機能要件

### FR-P4B-1: Space-Track CDM 取得

- 共通 [`spacetrack_client.py`](../backend/app/services/spacetrack_client.py)
- [`spacetrack_cdm_fetcher.py`](../backend/app/services/spacetrack_cdm_fetcher.py) — `cdm_public` JSON
- `POST /api/v1/cdm/fetch` — NORAD ID、Pc 下限、days_ahead
- 認証なし → 503、24h キャッシュ

### FR-P4B-2: アラート比較

- `POST /api/v1/cdm/compare-alert` — 衛星 TLE + CDM レコード
- 相手 NORAD の TLE をデブリカタログから解決
- UI「CDM アラート」タブ: 一覧 → 行クリックで CAS 比較

### FR-P4B-3: CDM エクスポート

- [`cdm_export.py`](../backend/app/services/cdm_export.py) — 等方 σ RTN 近似 KVN
- `POST /api/v1/cdm/export`
- 接近一覧「CDM エクスポート」→ クリップボード

---

## 3. スコープ外

- TLE 解析の非等方 encounter 共分散 → **Phase 4B-Ext で対応済み**（[`requirements-phase4b-ext.md`](requirements-phase4b-ext.md)）
- Webhook / メール通知 → **Phase 4B-Ext で Webhook スタブ対応済み**（本番 Slack/メールはスコープ外）
- クラウドデプロイ → **Phase 4C で Docker 対応済み**（[`deploy.md`](deploy.md)）

---

## 4. 成功条件

1. Space-Track 設定時 `/cdm/fetch` がレコードを返す
2. 未設定時 503 + 日本語メッセージ
3. アラート UI → CAS 比較まで操作可能
4. 接近イベントから CDM KVN エクスポート可能
5. `pytest tests/` 全件 PASS

---

## 5. 関連ファイル

| 種別 | パス |
|------|------|
| Space-Track client | `backend/app/services/spacetrack_client.py` |
| CDM fetch | `backend/app/services/spacetrack_cdm_fetcher.py` |
| Alert compare | `backend/app/services/cdm_alert_compare.py` |
| Export | `backend/app/services/cdm_export.py` |
| API | `backend/app/routers/cdm.py` |
| テスト | `tests/test_spacetrack_cdm_fetcher.py`, `tests/test_cdm_export.py`, `tests/test_cdm_router.py` |
