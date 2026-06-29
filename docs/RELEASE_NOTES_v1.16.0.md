# CAS v1.16.0 — Phase 10I Ops UI OIDC SSO

**Conjunction Alert Simulator** v1.16.0 — Ops UI / fleet・screening API 向け OIDC SSO（管理者 + 艦隊メールマッピング）。

## ハイライト

- **Phase 10I** — OIDC Authorization Code + PKCE
- HttpOnly 署名 cookie `cas_ops_session`
- 管理者 `OPS_OIDC_ADMIN_EMAILS` + 艦隊 `OPS_OIDC_FLEET_MAPPINGS`
- 既存 API Key 認証と併用
- Ops UI: SSO ログイン / ログアウト / 認証状態表示
- 監査 `auth.oidc_login`

## 環境変数

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

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 10I 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase10i.md |

## 使い方

`CAS_API_KEY_REQUIRED=true` + OIDC env を設定 → Ops タブで **SSO ログイン**。管理者は全艦隊、艦隊ユーザーはマッピングされた fleet のみ。API Key は自動化向けに引き続き利用可能。

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [v1.15.0 — Phase 10H API SLO](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.15.0)

**License:** MIT
