# CAS Phase 10S — 要件定義書

**版:** 10S  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10s.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第十九フェーズ。10Q で先送りした risk_level 別 per-fleet Prometheus メトリクスと Alertmanager 自動 push を実装する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `fleet_alert_metrics_service` 拡張、`alertmanager_push_service` |
| Metrics | `cas_fleet_alerts_by_risk_total`, `cas_fleet_high_risk_open_breach` |
| API | `POST /ops/prometheus/alertmanager/test` |
| env | `FLEET_ALERT_HIGH_RISK_THRESHOLD`, `ALERTMANAGER_*` |

---

## 2. 機能要件

### FR-10S-1: risk_level × status Gauge

- `fleet_id` × `risk_level`（high/medium/low）× `status`（6 状態）件数
- `cas_fleet_high_risk_open_breach` — open high ≥ 閾値で 1

### FR-10S-2: ルール雛形拡張

- `CASFleetHighRiskOpenAlerts` を既存 rule API に追加

### FR-10S-3: Alertmanager push

- breach 状態変化時のみ `POST /api/v2/alerts`
- open breach / high-risk open breach の 2 種

### FR-10S-4: Ops summary

- `open_high_count`, `open_medium_count`, `open_low_count`

---

## 3. 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `FLEET_ALERT_HIGH_RISK_THRESHOLD` | `1` | high open 閾値 |
| `ALERTMANAGER_PUSH_ENABLED` | `false` | opt-in |
| `ALERTMANAGER_URL` | — | 必須（push ON 時） |
| `ALERTMANAGER_BASIC_AUTH_USER` | — | optional |
| `ALERTMANAGER_BASIC_AUTH_PASSWORD` | — | optional |

---

## 4. スコープ外

- `open` への STM 巻き戻し、Alertmanager silences、Celery 定期 push

---

## 5. 成功条件

1. risk Gauge が `/metrics` に出る
2. rule 雛形に high-risk ルール含有
3. AM push default OFF で後方互換、pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 10R](requirements-phase10r.md)
- [Phase 10Q](requirements-phase10q.md)
