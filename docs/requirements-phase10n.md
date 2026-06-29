# CAS Phase 10N — 要件定義書

**版:** 10N  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10n.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第十四フェーズ。10H/10J の global API SLO を拡張し、fleet スコープ API Key / OIDC セッション単位の API 可用性を計測・表示する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `api_slo_fleet_context`, `fleet_api_availability_service` |
| DB | `api_slo_fleet_hourly_buckets` |
| API | `FleetSlaOut` fleet API フィールド、`/ops/sla/api-history?fleet_id=` |
| UI | Ops 艦隊ダッシュボード fleet API SLO + 7d トレンド |
| Metrics | `cas_fleet_api_availability_ratio`, `cas_fleet_api_slo_ok` |

---

## 2. 機能要件

### FR-10N-1: Fleet 帰属

- `get_auth_principal` で解決した fleet_id を ContextVar に設定
- 管理者キー / 未認証 → global のみ（既存）

### FR-10N-2: Fleet バケット

- 1h バケット、ローリング窓・5xx 定義は 10H 継承
- global バケットは常に維持

### FR-10N-3: DB 永続化

- `SLA_API_PERSIST_ENABLED=true` 時 fleet バケットも write-through

### FR-10N-4: Ops API

- `GET /ops/sla` — 各 `FleetSlaOut` に fleet API SLO フィールド
- `GET /ops/sla/api-history?fleet_id=` — fleet 日次履歴

### FR-10N-5: Ops UI

- 艦隊選択時 fleet API 行 + fleet 7d トレンド（サンプルなし時 global フォールバック）

---

## 3. 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `SLA_FLEET_API_SLO_ENABLED` | `false` | opt-in |

---

## 4. スコープ外

- PagerDuty resolve/ack、6×6 STM、per-fleet アラートルール自動生成

---

## 5. 成功条件

1. fleet API Key リクエストが艦隊バケットに計上
2. Ops UI で fleet API SLO 表示
3. default OFF で既存テスト不変
4. pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 10M](requirements-phase10m.md)
- [Phase 10J](requirements-phase10j.md)
- [Phase 10H](requirements-phase10h.md)
