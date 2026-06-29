# CAS Phase 10G — 要件定義書

**版:** 10G  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10g.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第七フェーズ。Phase 10F の自動 COLA スイープ後、改善 best preview があるアラートを条件付きで `mitigation_planned` へ自動遷移する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `maybe_auto_mitigation_plan` |
| Worker | `mitigation_sweep_task` 連携 |
| 通知 | `notify_mitigation_plan_auto` |
| UI | auto-planned バッジ |

---

## 2. 機能要件

### FR-10G-1: 自動対策計画遷移

- 10F sweep 完了後、改善 best ありで Celery 内 auto plan

### FR-10G-2: 任意 auto-ack

- `AUTO_ACK_BEFORE_MITIGATION_PLAN` で open→acknowledged 先行

### FR-10G-3: 改善なしはスキップ

- best 無し / `after_miss <= before_miss` は plan しない

### FR-10G-4: 追加通知

- `notify_mitigation_plan_auto`

### FR-10G-5: Ops UI

- auto-planned バッジ

### FR-10G-6: 監査

- `alert.mitigation_plan_auto`

---

## 3. 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `AUTO_MITIGATION_PLAN_ENABLED` | `false` | 自動対策計画遷移 |
| `AUTO_ACK_BEFORE_MITIGATION_PLAN` | `false` | open を先に acknowledged へ |

---

## 4. スコープ外

- SSO、API 99.9% SLA、DB スキーマ変更

---

## 5. 成功条件

1. auto sweep → improving best → mitigation_planned（条件付き）
2. pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 10F](requirements-phase10f.md)
- [Phase 10C](requirements-phase10c.md)
