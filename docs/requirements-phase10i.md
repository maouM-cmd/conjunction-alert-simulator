# CAS Phase 10I — 要件定義書

**版:** 10I  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10i.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第九フェーズ。Ops UI / fleet・screening API 向けに OIDC SSO（管理者 + 艦隊メールマッピング）を追加する。

| 変更箇所 | 内容 |
|---------|------|
| Auth | OIDC Authorization Code + PKCE、HttpOnly セッション cookie |
| API | `/api/v1/auth/*` |
| UI | SSO ログイン / ログアウト / ユーザー表示 |

---

## 2. 機能要件

### FR-10I-1: OIDC ログイン

- generic IdP（Auth0 / Azure AD / Keycloak 等）
- Authorization Code + PKCE

### FR-10I-2: 管理者 SSO

- `OPS_OIDC_ADMIN_EMAILS` に一致 → admin 権限

### FR-10I-3: 艦隊 SSO

- `OPS_OIDC_FLEET_MAPPINGS` JSON `{"fleet_uuid":["email@corp.com"]}`

### FR-10I-4: セッション cookie

- 署名付き `cas_ops_session`（HttpOnly）

### FR-10I-5: 既存 API Key 併用

- `CAS_API_KEY_REQUIRED=true` 時、cookie または `X-API-Key`

### FR-10I-6: Ops UI

- SSO ログイン / ログアウト / 認証状態表示

### FR-10I-7: 監査

- `auth.oidc_login`

**権限優先:** admin email → fleet mapping 最初の一致。不一致 → 403。

---

## 3. 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `OPS_OIDC_ENABLED` | `false` | OIDC 有効化 |
| `OPS_OIDC_ISSUER` | — | IdP issuer URL |
| `OPS_OIDC_CLIENT_ID` | — | |
| `OPS_OIDC_CLIENT_SECRET` | — | |
| `OPS_OIDC_REDIRECT_URI` | — | callback URL |
| `OPS_OIDC_ADMIN_EMAILS` | — | カンマ区切り |
| `OPS_OIDC_FLEET_MAPPINGS` | `{}` | JSON |
| `OPS_SESSION_SECRET` | — | cookie 署名 |
| `OPS_SESSION_TTL_HOURS` | `8` | |

---

## 4. スコープ外

- RBAC ロール、IdP グループ自動同期、SLO DB 永続化

---

## 5. 成功条件

1. OIDC ログイン → admin / fleet 権限で Ops API 利用可能
2. API Key 併用・regression PASS
3. pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 9E](requirements-phase9e.md)
- [Phase 10H](requirements-phase10h.md)
