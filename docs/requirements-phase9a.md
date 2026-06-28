# CAS Phase 9A — 要件定義書

**版:** 9A  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase9a.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 9（商用運用）の第一歩。エフェメラル batch（最大 25 衛星・都度リクエスト）から **PostgreSQL 上の登録艦隊** へ移行する。後続 9B（定期 Run）・9C（アラート triage）の前提。

| 変更箇所 | 内容 |
|---------|------|
| 新規 DB 層 | `fleets`, `satellites`, `tle_revisions` |
| 新規 API | `/api/v1/fleets` CRUD + 衛星登録 |
| [`docker-compose.yml`](../docker-compose.yml) | `postgres` サービス追加 |
| 既存 batch | ad-hoc 解析として互換維持 |

---

## 2. 機能要件

### FR-P9A-1: Fleet CRUD

- `POST /api/v1/fleets` — name, description, tags
- `GET /api/v1/fleets` / `GET /api/v1/fleets/{id}`
- `PATCH /api/v1/fleets/{id}` / `DELETE /api/v1/fleets/{id}`（論理削除可）

### FR-P9A-2: Satellite Registry

- `POST /api/v1/fleets/{fleet_id}/satellites` — name, norad_id, tle（3行）
- `GET /api/v1/fleets/{fleet_id}/satellites` — ページネーション（default 100, max 500）
- `PATCH /api/v1/satellites/{id}` — TLE 更新時に revision 自動追加
- `DELETE /api/v1/satellites/{id}`

### FR-P9A-3: TLE Revision History

- `tle_revisions`: satellite_id, tle, created_at
- 最新 2 世代保持（rollback API 任意: `POST .../satellites/{id}/rollback`）

### FR-P9A-4: 互換

- 既存 `POST /api/v1/conjunctions/batch`（ad-hoc TLE リスト）は変更なし
- DB 未設定時: fleet API は 503、既存 conjunction API は従来どおり動作（env `DATABASE_URL` 未設定フォールバック）

---

## 3. データモデル（案）

| テーブル | 主要カラム |
|---------|-----------|
| `fleets` | id, name, description, tags, created_at, updated_at |
| `satellites` | id, fleet_id, name, norad_id, tle, tle_updated_at, active |
| `tle_revisions` | id, satellite_id, tle, created_at |

---

## 4. 技術方針

- **ORM:** SQLAlchemy 2.x
- **Migration:** Alembic
- **接続:** `DATABASE_URL` env（例 `postgresql://cas:cas@postgres:5432/cas`）
- **テスト:** pytest + SQLite または testcontainers PostgreSQL

---

## 5. スコープ外（9A）

- 定期スクリーニング（9B）
- アラート永続・triage（9C）
- 1,000+ チャンク worker（9D）
- API Key 認証（9E）

---

## 6. 成功条件

1. fleet / satellite CRUD が REST で動作
2. TLE 更新で revision が残る
3. DB なし環境で既存 batch / conjunction regression なし
4. `pytest tests/` 全件 PASS

---

## 7. 関連ドキュメント

- [商用運用ロードマップ](requirements-commercial-ops.md)
- [API 設計](api-design.md)
- [implementation_plan.md](../implementation_plan.md)
