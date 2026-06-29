# CAS Phase 10Q — 要件定義書

**版:** 10Q  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10q.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第十七フェーズ。艦隊別 conjunction alert 件数を Prometheus に export し、Ops API で alerting rule 雛形を自動生成する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `fleet_alert_metrics_service` |
| Metrics | `cas_fleet_alerts_total`, `cas_fleet_open_alerts_breach` |
| API | `GET /ops/prometheus/fleet-alert-rules` |
| env | `FLEET_ALERT_METRICS_ENABLED` |

---

## 2. 機能要件

### FR-10Q-1: per-fleet Gauge

- `fleet_id` × `status`（5 状態）件数
- active 艦隊のみ

### FR-10Q-2: breach 指標

- `open_count > FLEET_ALERT_OPEN_THRESHOLD` で `cas_fleet_open_alerts_breach=1`

### FR-10Q-3: ルール雛形 API

- YAML / JSON 形式で Prometheus alerting rule を返却
- fleet スコープ key は自艦隊のみ、admin は全艦隊

### FR-10Q-4: 後方互換

- `FLEET_ALERT_METRICS_ENABLED=false` で既存 `/metrics` 挙動維持

---

## 3. 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `FLEET_ALERT_METRICS_ENABLED` | `false` | opt-in |
| `FLEET_ALERT_OPEN_THRESHOLD` | `10` | open 件数閾値 |

---

## 4. スコープ外

- 6×6 STM、risk_level 別メトリクス、Alertmanager 自動 push

---

## 5. 成功条件

1. metrics ON で per-fleet Gauge が `/metrics` に出る
2. Ops API で rule 雛形取得可能
3. pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 10P](requirements-phase10p.md)
- [Phase 10N](requirements-phase10n.md)
