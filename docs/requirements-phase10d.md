# CAS Phase 10D — 要件定義書

**版:** 10D  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10d.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第四フェーズ。永続化アラートに CDM/RTN 共分散で Pc を再計算し、screening Pc と refined Pc を比較可能にする。

| 変更箇所 | 内容 |
|---------|------|
| DB | `alert_pc_refinements` |
| API | POST/GET pc-refine |
| UI | Ops「Pc 再計算」 |

---

## 2. 機能要件

### FR-10D-1: Pc 再計算

- TCA 前後 1h 伝播、CDM RTN 優先、TLE RTN フォールバック

### FR-10D-2: 永続化

- 試算履歴を複数件保存（`conjunction_alerts.pc` は screening 値のまま）

### FR-10D-3〜4: API

- `POST /api/v1/ops/alerts/{id}/pc-refine`
- `GET /api/v1/ops/alerts/{id}/pc-refinements`

### FR-10D-5〜6: Ops UI

- screening vs refined 表示、「Pc 再計算」ボタン

### FR-10D-7: 監査

- `alert.pc_refine`

---

## 3. スコープ外

- alert.pc 上書き、SSO、COLA 自動実行

**Pc 保存:** foster 値、`pc_method`: `cdm_rtn` | `tle_rtn`

---

## 4. 成功条件

1. Pc 再計算 → DB 保存 → UI 比較表示
2. pytest 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 10C](requirements-phase10c.md)
- [Phase 10A](requirements-phase10a.md)
