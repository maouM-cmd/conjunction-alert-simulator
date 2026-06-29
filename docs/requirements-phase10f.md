# CAS Phase 10F — 要件定義書

**版:** 10F  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10f.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第六フェーズ。Phase 10E の自動 Pc 再計算・エスカレーション後、条件を満たすアラートに Δv スイープを Celery で自動実行し best preview を永続化・通知する。

| 変更箇所 | 内容 |
|---------|------|
| DB | `alert_mitigation_previews.trigger_source` |
| Worker | `mitigation_sweep_task` |
| 通知 | `notify_mitigation_best` |
| UI | mitigation auto バッジ |

---

## 2. 機能要件

### FR-10F-1: 自動 Δv スイープ

- 10E refine 完了後、条件付きで Celery enqueue

### FR-10F-2: trigger_source

- `manual` / `screening_auto` を preview 行に記録

### FR-10F-3: best 通知

- best preview あり時に追加 Webhook/Slack/SMTP

### FR-10F-4: 手動維持

- 手動 preview/sweep は `trigger_source=manual`

### FR-10F-5: Ops UI

- latest preview に auto バッジ

### FR-10F-6: 監査

- `alert.mitigation_sweep_auto`

---

## 3. 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `AUTO_MITIGATION_SWEEP_ENABLED` | `false` | 自動 Δv スイープ |
| `AUTO_MITIGATION_SWEEP_ON_ESCALATION_ONLY` | `true` | エスカレーション済みのみ |
| `AUTO_MITIGATION_SWEEP_PC_MIN` | `1e-5` | ON_ESCALATION_ONLY=false 時の refined Pc 閾値 |

---

## 4. スコープ外

- SSO、API 99.9% SLA、`mitigation_planned` 自動遷移

---

## 5. 成功条件

1. エスカレーション後 auto sweep → best 通知
2. pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 10E](requirements-phase10e.md)
- [Phase 10C](requirements-phase10c.md)
