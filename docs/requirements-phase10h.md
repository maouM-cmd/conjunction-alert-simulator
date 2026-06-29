# CAS Phase 10H — 要件定義書

**版:** 10H  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10h.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第八フェーズ。Phase 10B の HTTP Counter を拡張し、ローリング窓で API 可用性 **99.9%** SLO を Ops API/UI と Prometheus で可視化する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `api_availability_service` — 1h バケット・ローリング可用性 |
| Metrics | `cas_api_availability_ratio`, `cas_api_slo_ok` |
| API | `GET /api/v1/ops/sla` に API SLO フィールド |
| UI | Ops summary に API availability OK/BREACH |

---

## 2. 機能要件

### FR-10H-1: ローリング可用性

- 可用性 = `(total - 5xx) / total`
- 1 時間バケット、窓 = `SLA_API_ROLLING_WINDOW_HOURS`（default 720h）

### FR-10H-2: SLO 判定

- 目標 `SLA_API_TARGET_PERCENT`（default 99.9）と比較 → `api_slo_ok`
- サンプル 0 → ratio null、`api_slo_ok=true`（N/A）

### FR-10H-3: Prometheus

- `cas_api_availability_ratio`, `cas_api_slo_ok` Gauge

### FR-10H-4: Ops SLA API

- `GET /api/v1/ops/sla` レスポンスに global API SLO フィールド

### FR-10H-5: Ops UI

- summary に API availability 行

### FR-10H-6: 監視ドキュメント

- api-design に 99.9% Grafana クエリ例

**可用性定義:** 5xx のみエラー。4xx は success。`/metrics` は計測除外。

---

## 3. 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `SLA_API_TARGET_PERCENT` | `99.9` | API SLO 目標（%） |
| `SLA_API_ROLLING_WINDOW_HOURS` | `720` | ローリング窓（30 日） |

---

## 4. スコープ外

- SSO/OIDC、SLO DB 永続化、PagerDuty、共分散伝播強化

---

## 5. 成功条件

1. 5xx 混入で availability 低下・SLO breach 検出
2. Ops UI / Prometheus / `/ops/sla` で SLO 表示
3. pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 10B](requirements-phase10b.md)
- [Phase 10G](requirements-phase10g.md)
