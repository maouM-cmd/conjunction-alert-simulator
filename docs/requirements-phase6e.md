# CAS Phase 6E — 要件定義書

**版:** 6E  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase6e.md`）

---

## 1. 概要

Phase 6（公開・Live Demo・CI/CD）完了後、ポートフォリオ仕上げを行う。Qiita 原稿、GitHub Social Preview 素材、v1.1.1 リリース、CI 最適化。

| サブフェーズ | 内容 |
|-------------|------|
| 6E-1 | Qiita 原稿更新 + 投稿手順 |
| 6E-2 | GitHub Social Preview 素材 + 設定手順 |
| 6E-3 | v1.1.1 リリース（Phase 6 集約） |
| 6E-4 | CI 最適化（pytest 一本化、verify 待機短縮） |

---

## 2. 機能要件

### FR-P6E-1: Qiita

- [`docs/demo/blog-draft.md`](demo/blog-draft.md) — Zenn 原稿と Phase 5/6 整合
- [`docs/publish-qiita.md`](publish-qiita.md) — 投稿チェックリスト

### FR-P6E-2: Social Preview

- [`.github/social-preview.png`](../.github/social-preview.png) — 素材（Settings アップロード用）
- [`docs/publish-github-social-preview.md`](publish-github-social-preview.md)

### FR-P6E-3: v1.1.1 Release

- [`CHANGELOG.md`](../CHANGELOG.md)、[`docs/RELEASE_NOTES_v1.1.1.md`](RELEASE_NOTES_v1.1.1.md)
- tag `v1.1.1` + GitHub Release

### FR-P6E-4: CI 最適化

- [`test.yml`](../.github/workflows/test.yml) — PR のみ
- [`deploy.yml`](../.github/workflows/deploy.yml) — Hook 有無で verify 待機時間可変

---

## 3. スコープ外

- Qiita ブラウザ実投稿
- Space-Track / Slack Bot 機能拡張

---

## 4. 成功条件

1. `blog-draft.md` が Live Demo / Phase 5/6 を含む
2. Social Preview 素材 + 手順書がリポに存在
3. `v1.1.1` Release 公開
4. `main` push で pytest 1 回（deploy workflow のみ）

---

## 5. 関連ドキュメント

- [Phase 6B](requirements-phase6b.md) — CI/CD
- [Zenn 原稿](demo/blog-zenn.md)
- [公開チェックリスト](publish-checklist-v1.1.0.md)
