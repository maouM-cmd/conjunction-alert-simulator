# CAS Phase 4B-Ext — 要件定義書

**版:** 4B-Ext  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase4b-ext.md`）

---

## 1. 概要

Phase 4C 完了後、TLE 由来の RTN 非等方共分散を encounter plane Pc に統合し、Webhook 通知スタブを追加する。

| サブフェーズ | 内容 |
|-------------|------|
| 4B-Ext-1 | TLE RTN 非等方 → encounter 2×2 共分散 |
| 4B-Ext-2 | `use_anisotropic_cov` opt-in（advanced Pc 時） |
| 4B-Ext-3 | Webhook 通知スタブ + テスト API |
| 4B-Ext-4 | ドキュメント + pytest + ship |

---

## 2. 機能要件

### FR-P4BE-1: TLE 非等方 encounter 共分散

- [`tle_rtn_covariance.py`](../backend/app/services/tle_rtn_covariance.py)
- RTN スケール: R=2.0, T=0.5, N=0.5（ベース σ は TLE 経過日数推定）
- CDM パスと同一の TEME 合成 → encounter 2×2 射影
- `use_advanced_pc=true` **かつ** `use_anisotropic_cov=true` のときのみ適用

### FR-P4BE-2: API / スキーマ

- `ConjunctionsRequest` / `BatchConjunctionsRequest`: `use_anisotropic_cov: bool = false`
- `ConjunctionOut.covariance_source`: `"isotropic"` | `"tle_rtn_anisotropic"` | null
- デフォルト `false` で Phase 4A-Ext 挙動維持

### FR-P4BE-3: Webhook 通知スタブ

- [`webhook_notifier.py`](../backend/app/services/webhook_notifier.py)
- 環境変数: `ALERT_WEBHOOK_URL`, `ALERT_PC_THRESHOLD`（デフォルト `1e-5`）
- `POST /api/v1/alerts/webhook/test` — テスト ping（URL 未設定 → 503）
- `ConjunctionsRequest.notify_webhook`: high/medium かつ Pc ≥ threshold を POST

### FR-P4BE-4: UI

- 「高精度 Pc」ON 時のみ有効な「非等方 RTN 共分散」チェックボックス（単一 + batch）
- 「Webhook 通知」チェックボックス（単一衛星）
- 一覧: `covariance_source === "tle_rtn_anisotropic"` 時 `(非等方 σ)` 表示

---

## 3. スコープ外

- CDM 共分散の一覧 API 自動適用（CDM compare / compare-alert のみ）
- メール / Slack Bot 本番連携（汎用 Webhook URL のみ）
- Phase 4D ポートフォリオ素材

---

## 4. 成功条件

1. `use_anisotropic_cov=false` で従来 Pc 維持
2. `use_advanced_pc=true` + `use_anisotropic_cov=true` で encounter 2×2 非等方 Alfriend
3. `ALERT_WEBHOOK_URL` 設定時 `/alerts/webhook/test` が 200
4. `notify_webhook=true` で high イベントが Webhook に POST（mock テスト）
5. `pytest tests/` 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 4B](requirements-phase4b.md) — スコープ外だった非等方/Webhook を本フェーズで対応
- [API 設計書](api-design.md)
- [アーキテクチャ](architecture.md)
