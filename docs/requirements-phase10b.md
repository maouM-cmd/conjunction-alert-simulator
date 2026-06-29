# CAS Phase 10B — 要件定義書

**版:** 10B  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10b.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第二フェーズ。Phase 9E FR-9E-4 で文書のみだった SLA 目標を Prometheus と Ops API で計測可能にする。

| 変更箇所 | 内容 |
|---------|------|
| Metrics | HTTP Counter、screening lag Gauge |
| API | `GET /api/v1/ops/sla` |
| UI | Ops summary に lag OK/OVERDUE |

---

## 2. 機能要件

### FR-10B-1: HTTP メトリクス

- `cas_http_requests_total{method, status_class}` を Prometheus 出力
- `/metrics` パスはカウント除外

### FR-10B-2: スクリーニング lag

- 艦隊ごと: 最終 **completed 親 run** の `finished_at` からの経過秒
- 対象: `active=true` の schedule を持つ艦隊

### FR-10B-3: overdue 件数

- lag > `SLA_SCREENING_MAX_LAG_HOURS`（default 24）の艦隊数

### FR-10B-4: Ops SLA API

- `GET /api/v1/ops/sla?fleet_id=` — JSON サマリ

### FR-10B-5: Ops UI

- summary に screening lag + OK/OVERDUE 表示

### FR-10B-6: 監視ドキュメント

- api-design に Prometheus/Grafana クエリ例

---

## 3. SLA 判定

- schedule あり・completed 親 run なし → `sla_ok=false`
- schedule なし → `has_active_schedule=false`（overdue 対象外）
- API 99.5% は Prometheus 外部集計（アプリは Counter のみ）

---

## 4. スコープ外

- 月次 SLA の DB 永続化
- PagerDuty 連携
- SSO / COLA 拡張

---

## 5. 成功条件

1. `/metrics` に lag / HTTP counter が出力される
2. Ops UI で lag 表示
3. pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 10A](requirements-phase10a.md)
- [Phase 9E](requirements-phase9e.md)
