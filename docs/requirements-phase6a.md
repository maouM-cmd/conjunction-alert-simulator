# CAS Phase 6A — 要件定義書

**版:** 6A  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase6a.md`）

---

## 1. 概要

Phase 5（v1.1.0 tag 済み）完了後、ポートフォリオ公開を完結させる。GitHub Release ページ作成手順、Zenn 投稿チェックリスト v1.1.0 更新、README 訴求仕上げを行う。

| サブフェーズ | 内容 |
|-------------|------|
| 6A-1 | GitHub Release v1.1.0 公開手順 + Release ページ作成 |
| 6A-2 | Zenn 投稿チェックリスト v1.1.0 更新 |
| 6A-3 | README ポートフォリオ訴求（技術記事欄・v1.1 ハイライト） |
| 6A-4 | GitHub リポ About / Topics 推奨文 |

---

## 2. 機能要件

### FR-P6A-1: GitHub Release

- [`docs/RELEASE_NOTES_v1.1.0.md`](RELEASE_NOTES_v1.1.0.md) — Release 本文
- [`docs/publish-github-release.md`](publish-github-release.md) — `gh release create` 手順
- Git tag `v1.1.0`（push 済み）→ GitHub Release ページ

### FR-P6A-2: Zenn 投稿

- [`docs/demo/blog-zenn.md`](demo/blog-zenn.md) — Phase 5 原稿（`published: false`）
- [`docs/publish-zenn.md`](publish-zenn.md) — v1.1.0 向けチェックリスト
- [`docs/publish-checklist-v1.1.0.md`](publish-checklist-v1.1.0.md) — マスター実行順

### FR-P6A-3: README 訴求

- v1.1.0 / Phase 5 一行サマリ（冒頭）
- 「技術記事」セクション（Zenn 準備中 → 公開後 URL）
- ローカル 2 分デモを primary CTA、Live Demo は TBD 明記

### FR-P6A-4: GitHub リポ設定

- About Description / Topics 推奨文（[`publish-checklist-v1.1.0.md`](publish-checklist-v1.1.0.md)）

---

## 3. スコープ外

- Render / Fly.io **実デプロイ** と Live Demo URL 更新 → **Phase 6C**
- GitHub Actions → Render 自動デプロイ → **Phase 6B**
- Zenn / GitHub Release の**ブラウザからの実操作**（手順・素材まで）
- Qiita 実投稿（転用手順のみ [`publish-zenn.md`](publish-zenn.md)）

---

## 4. 成功条件

1. `gh release create v1.1.0 --notes-file docs/RELEASE_NOTES_v1.1.0.md` がそのまま実行できる
2. `blog-zenn.md` を Zenn にコピペ → 画像・Phase 5 節がプレビュー OK
3. README 先頭〜技術記事欄が portfolio 向けに読める
4. Live Demo は「デプロイ後に追記」と明記のまま
5. `pytest tests/` ローカル PASS

---

## 5. 関連ドキュメント

- [Phase 5D](requirements-phase5d.md) — デモ刷新・v1.1.0 tag
- [Phase 5A](requirements-phase5a.md) — v1.0.0 Release / Zenn 原稿テンプレ
- [Release Notes v1.1.0](RELEASE_NOTES_v1.1.0.md)
