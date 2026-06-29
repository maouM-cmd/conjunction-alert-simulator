# CAS Phase 10A — 要件定義書

**版:** 10A  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10a.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第一フェーズ。永続化アラートから既存 maneuver preview を実行し、回避試算結果を Ops ワークフローに統合する。

| 変更箇所 | 内容 |
|---------|------|
| DB | `alert_mitigation_previews` |
| API | POST/GET mitigation-preview |
| UI | Ops タブ「回避試算」ボタン |

---

## 2. 機能要件

### FR-10A-1: アラート連動試算

- 衛星 TLE（DB）+ デブリ TLE（catalog `find_tle_by_norad_id`）で preview 実行

### FR-10A-2: 永続化

- 試算履歴を複数件保存

### FR-10A-3〜4: API

- `POST /api/v1/ops/alerts/{id}/mitigation-preview`
- `GET /api/v1/ops/alerts/{id}/mitigation-previews`

### FR-10A-5: Ops UI

- アラート行から回避試算、結果表示

### FR-10A-6: 監査

- `alert.mitigation_preview` を audit_logs に記録

---

## 3. スコープ外

- 燃料最適 Δv 自動探索
- COLA 自動実行
- ad-hoc `/maneuver/preview` 変更

---

## 4. 成功条件

1. アラートから試算 → DB 保存 → UI 表示
2. pytest 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 9E](requirements-phase9e.md)
- [商用運用ロードマップ](requirements-commercial-ops.md)
