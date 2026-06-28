# CAS 商用コンステレーション運用 — 要件定義書

**版:** 1.0（Commercial Ops）  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-commercial-ops.md`）  
**前提:** ポートフォリオ版 CAS v1.2.2（[`requirements.md`](requirements.md)）をベースに、大規模コンステ運用へ拡張するロードマップ

---

## 1. 概要

| 項目 | 内容 |
|------|------|
| 名称 | Conjunction Alert Simulator — Commercial Ops Track |
| 概要 | 1,000+ 衛星規模のコンステに対し、接近スクリーニング・アラート triage・通知を **永続化・定期実行** できる運用基盤へ拡張 |
| 目的 | 商用コンステ運用システムの主要ワークフロー（艦隊登録 → 定期スクリーニング → アラート管理 → 通知）を CAS アーキテクチャ上に実装 |
| 現状成熟度 | **約 35%**（v1.2.2：解析・通知はあるが DB / スケジュール / triage なし） |
| Phase 9 完了目標 | **約 70%**（運用ワークフロー軸） |
| 100% 接近目標 | Phase 10+（COLA、燃料最適化、SSO、ADR 等） |

**ターゲット規模:** 登録衛星 **1,000〜10,000**、全艦隊 1 スクリーニングサイクル **24 時間以内**

**優先軸:** 運用ワークフロー（艦隊登録・定期スクリーニング・アラート履歴・オペ triage）

---

## 2. ステークホルダー

| 利用者 | 目的 | Phase 9 で満たすこと |
|--------|------|---------------------|
| コンステ運用オペ | 日次接近監視 | 定期スクリーニング + アラート一覧 + 状態管理 |
| ミッションオペ | 回避判断 | 永続アラート履歴、TCA/Pc トレンド、通知 |
| SSA / 安全担当 | 監査・エスカレーション | 監査ログ、Run 履歴、重複抑制 |
| 開発者 / SRE | スケール・可用性 | PostgreSQL + Redis + worker、Prometheus |
| OSS 閲覧者 | 学習・デモ | 既存 ad-hoc API / UI 互換維持 |

**非ターゲット（Phase 9）:** 課金 SaaS、Space-Track マルチテナント OAuth、ADR ハードウェア連携

---

## 3. 成熟度モデル

| レベル | 名称 | 内容 | CAS |
|--------|------|------|-----|
| L1 | デモ | 手動 TLE → 単発解析 | Phase 1〜4 |
| L2 | 拡張デモ | Pc/CDM/batch/通知 | **v1.2.2（現在地）** |
| L3 | 運用パイロット | 艦隊 DB + 定期 Run + アラート永続 | Phase 9A〜9C |
| L4 | 大規模運用 | 1,000+ sat、worker 水平スケール、監査 | Phase 9D〜9E |
| L5 | 商用 SLA | COLA 自動化、SSO、99.9%+ SLA | Phase 10+ |

---

## 4. 現状ギャップ（v1.2.2 ベースライン）

| 商用運用要素 | 現状 | ギャップ |
|-------------|------|---------|
| 艦隊管理 | batch 最大 25 衛星、都度リクエスト | 永続 registry なし |
| 定期スクリーニング | 手動 UI/API のみ | scheduler / worker なし |
| アラート履歴 | なし | DB なし |
| オペ triage | なし | ack / 状態遷移なし |
| 通知 | Webhook / Slack / SMTP | 新規 vs 既知の区別なし |
| 認証 | なし | API Key / RBAC なし |
| 大規模処理 | ProcessPool 同期・単一ホスト | 分散キューなし |

参照: [`batch_analysis.py`](../backend/app/services/batch_analysis.py) `MAX_SATELLITES = 25`

---

## 5. Phase 9 ロードマップ

実装順: **9A → 9B → 9C → 9D → 9E**

### Phase 9A — Fleet Registry & Persistence

**目的:** エフェメラル batch から「登録艦隊」へ

| ID | 要件 |
|----|------|
| FR-9A-1 | PostgreSQL: `fleets`, `satellites`（name, norad_id, tle, tle_updated_at, tags, fleet_id） |
| FR-9A-2 | REST: 艦隊 CRUD、`POST /api/v1/fleets/{id}/satellites`、一覧・更新・削除 |
| FR-9A-3 | TLE バージョン履歴（最低 1 世代 rollback） |
| FR-9A-4 | 既存 `/conjunctions/batch` は ad-hoc 解析として互換維持 |

**技術方針:** SQLAlchemy + Alembic、`docker-compose.yml` に `postgres` 追加

詳細: [`requirements-phase9a.md`](requirements-phase9a.md)

---

### Phase 9B — Scheduled Screening Jobs

**目的:** 手動解析 → 定期自動スクリーニング

| ID | 要件 |
|----|------|
| FR-9B-1 | `screening_schedules`（cron 式、fleet_id、threshold_km、Pc/高度フィルタ設定） |
| FR-9B-2 | Redis + worker（Celery または RQ）でジョブ enqueue |
| FR-9B-3 | `screening_runs`: started_at, finished_at, status, satellite_count, event_count, degraded |
| FR-9B-4 | 失敗リトライ・デッドレター、Run 完了通知（[`webhook_notifier.py`](../backend/app/services/webhook_notifier.py) 再利用） |

**NFR-9B-1:** 1,000 衛星を **24h 以内** に 1 サイクル（worker 水平スケール前提）

---

### Phase 9C — Alert Lifecycle & Ops Dashboard

**目的:** オペレータ triage ワークフロー

| ID | 要件 |
|----|------|
| FR-9C-1 | `conjunction_alerts` 永続化（satellite_id, debris_norad, tca, pc, risk_level, screening_run_id） |
| FR-9C-2 | 状態: `open` → `acknowledged` → `mitigation_planned` → `closed` / `false_positive` |
| FR-9C-3 | 重複抑制: 同一 sat-debris **±24h** 窓でマージ |
| FR-9C-4 | Ops UI: 艦隊サマリ、アラート一覧、状態フィルタ、コメント（任意） |
| FR-9C-5 | 通知は **新規 open のみ**（既存 notify 経路拡張） |

---

### Phase 9D — Scale-Out（1,000+ 衛星）

**目的:** `MAX_SATELLITES=25` 壁の突破

| ID | 要件 |
|----|------|
| FR-9D-1 | 登録艦隊上限 **10,000**（設定可能）、スクリーニングは **チャンク単位**（例 50 sat/job） |
| FR-9D-2 | ワーカー複数プロセス / 複数ホスト、`BATCH_MAX_WORKERS` → worker 設定へ移行 |
| FR-9D-3 | デブリ catalog **高度帯プリフィルタ**を worker デフォルト化（Phase 7C 再利用） |
| FR-9D-4 | Space-Track CDM 自動マージ: レートリミット + キュー（Phase 8A 再利用） |
| FR-9D-5 | `/metrics` Prometheus（run 時間、queue 深さ、open alert 件数） |

---

### Phase 9E — Platform Baseline

| ID | 要件 |
|----|------|
| FR-9E-1 | API Key 認証（fleet スコープ） |
| FR-9E-2 | 監査ログ（alert 状態変更、TLE 更新、schedule 変更） |
| FR-9E-3 | `/health` 拡張: PostgreSQL / Redis / worker 生存 |
| FR-9E-4 | SLA 目標: API **99.5%**、スクリーニング遅延 **< 24h** |

---

## 6. 目標アーキテクチャ（Phase 9 完了時）

```
Ops UI / REST API
       │
       ▼
  PostgreSQL ◄── screening_runs, conjunction_alerts, fleets, satellites
       │
       ▼
  Redis Queue ──► Screening Workers ──► analysis.py / batch ロジック
       │                                      │
       └──────────────────────────────────────┴──► webhook_notifier (Slack/SMTP/…)
```

---

## 7. 非機能要件（商用）

| ID | 要件 | 目標値 |
|----|------|--------|
| NFR-C-1 | 登録衛星数 | 10,000（設定上限） |
| NFR-C-2 | 全艦隊スクリーニング周期 | ≤ 24h |
| NFR-C-3 | アラート永続 RPO | ≤ 5 min（worker commit 単位） |
| NFR-C-4 | API 可用性（Phase 9E） | 99.5% / 月 |
| NFR-C-5 | 監査ログ保持 | ≥ 90 日 |
| NFR-C-6 | 既存 ad-hoc API | Phase 9 後も regression なし |

---

## 8. スコープ外（Phase 9）

- OAuth SSO / マルチテナント Space-Track
- COLA 自動生成・燃料最適化
- ADR 物理シミュレーション
- 課金・請求
- HTML メール / Block Kit（Phase 8B スコープ外の延長）
- Starlink 級 **秒単位** リアルタイム SSA 融合

**Phase 10 以降:** 精度軸（COLA、共分散伝播強化）、L5 SLA

---

## 9. 成功条件・KPI

| KPI | v1.2.2 現状 | Phase 9 完了目標 |
|-----|------------|-----------------|
| 商用運用成熟度（WF 軸） | ~35% | ~70% |
| 登録衛星数 | 25（都度 batch） | 10,000 |
| スクリーニング | 手動 | cron 自動 + Run 履歴 |
| アラート triage | なし | 5 状態 + Ops UI |
| データ永続 | なし | PostgreSQL |
| 全艦隊 1 周 | N/A | 24h 以内 |

1. Phase 9A: 艦隊 CRUD + TLE 履歴が API/UI から操作可能
2. Phase 9B: スケジュール Run が worker 経由で完走し Run 履歴が残る
3. Phase 9C: オペが alert 状態を遷移でき、新規 open のみ通知
4. Phase 9D: 1,000 衛星デモ fleet で 24h サイクル達成（ベンチ記録）
5. Phase 9E: API Key + 監査ログ + `/health` 拡張
6. `pytest tests/` 全件 PASS（既存 + Phase 9 追加）

---

## 10. 関連ドキュメント

- [Phase 1 要件（ポートフォリオ版）](requirements.md)
- [Phase 9A 詳細](requirements-phase9a.md)
- [API 設計](api-design.md)
- [implementation_plan.md](../implementation_plan.md)
