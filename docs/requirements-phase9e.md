# CAS Phase 9E — 要件定義書

**版:** 9E  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase9e.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 9 第五フェーズ。商用運用の認証・監査・readiness を追加し、成熟度 L4 を完成させる。

| 変更箇所 | 内容 |
|---------|------|
| 認証 | fleet スコープ API Key（デフォルト OFF） |
| 監査 | alert / TLE / schedule 操作ログ |
| 監視 | `/health` PostgreSQL / Redis / worker チェック |

---

## 2. 機能要件

### FR-9E-1: API Key 認証

- `X-API-Key` ヘッダ、`CAS_API_KEY_REQUIRED=false` デフォルト
- true 時: `/api/v1/fleets`, `/screening`, `/ops` を保護
- ad-hoc 解析 API は公開維持（NFR-C-6）

### FR-9E-2: 監査ログ

- alert 状態遷移、TLE 更新、schedule CRUD
- `GET /api/v1/ops/audit`、90 日保持

### FR-9E-3: `/health` 拡張

- `checks.postgres` / `checks.redis` / `checks.worker`
- HTTP 200 維持、`status`: ok | degraded

### FR-9E-4: SLA 目標（文書のみ）

- API 可用性 **99.5%** / 月
- スクリーニング遅延 **< 24h**

---

## 3. スコープ外

- OAuth / SSO / RBAC
- ad-hoc batch / conjunction / cdm への認証

---

## 4. 成功条件

1. API Key 有効時に fleet スコープが enforced
2. 監査対象操作で audit 行が残る
3. `/health` に checks フィールド
4. pytest 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 9D](requirements-phase9d.md)
- [商用運用ロードマップ](requirements-commercial-ops.md)
