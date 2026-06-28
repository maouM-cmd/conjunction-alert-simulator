# CAS Phase 5C — 要件定義書

**版:** 5C  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase5c.md`）

---

## 1. 概要

Phase 5B 完了後、Webhook 運用連携と CDM 共分散の一覧 API 適用、通知 UI を強化する。

| サブフェーズ | 内容 |
|-------------|------|
| 5C-1 | Slack Incoming Webhook ペイロード |
| 5C-2 | `/conjunctions` への CDM 共分散 opt-in |
| 5C-3 | Webhook 結果返却 + batch 通知 + UI |
| 5C-4 | ドキュメント + pytest + ship |

---

## 2. 機能要件

### FR-P5C-1: Slack Webhook

- `ALERT_WEBHOOK_FORMAT=generic|slack`
- [`webhook_notifier.py`](../backend/app/services/webhook_notifier.py)

### FR-P5C-2: CDM σ on 一覧 API

- `ConjunctionsRequest.cdm_text` + `apply_cdm_covariance`
- [`cdm_pc_enrichment.py`](../backend/app/services/cdm_pc_enrichment.py)
- `ConjunctionOut.sigma_source`

### FR-P5C-3: 通知 UI

- Webhook テストボタン、解析後結果表示
- batch `notify_webhook` fleet 一括 POST
- CDM 比較 → 単一衛星解析への引き渡し

---

## 3. スコープ外

- Slack Bot / OAuth / メール SMTP
- Space-Track フル CDM（RTN 共分散）自動取得
- Render 実デプロイ / GitHub Actions 自動デプロイ

---

## 4. 成功条件

1. Slack format で readable `text` POST
2. `apply_cdm_covariance=true` で `sigma_source=cdm_covariance`
3. UI Webhook テスト + 結果表示
4. batch Webhook 動作
5. `pytest tests/` 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 4B-Ext](requirements-phase4b-ext.md) — スコープ外 2 項目 → 本フェーズ
- [Phase 5B](requirements-phase5b.md)
