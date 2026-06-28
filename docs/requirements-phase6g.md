# CAS Phase 6G — 要件定義書

**版:** 6G  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase6g.md`）

---

## 1. 概要

Phase 6F（Qiita URL・Social Preview）完了後、公開コンテンツの仕上げを行う。Qiita 本文・タグ差し替え、Zenn 本番への Qiita 相互リンク同期。

| サブフェーズ | 内容 |
|-------------|------|
| 6G-1 | Qiita 既存記事更新（本文 + タグ） |
| 6G-2 | Zenn 本番記事に Qiita 相互リンク |
| 6G-3 | 投稿・更新手順ドキュメント整備 |
| 6G-4 | docs commit / push（tag 新設なし） |

---

## 2. 機能要件

### FR-P6G-1: Qiita 記事更新

- Item ID: `986e533b16b348f7d5e4`
- 正本: [`docs/demo/blog-draft.md`](demo/blog-draft.md)
- [`scripts/publish_qiita_item.ps1`](../scripts/publish_qiita_item.ps1) `-Update`（PATCH API）
- タグ: `Python`, `FastAPI`, `宇宙`, `OSS`, `Docker`, `SGP4`

### FR-P6G-2: Zenn 相互リンク

- 正本: [`docs/demo/blog-zenn.md`](demo/blog-zenn.md) まとめ節
- Zenn Web エディタで本番記事を同期

### FR-P6G-3: ドキュメント

- [`docs/publish-qiita.md`](publish-qiita.md) — 既存記事更新手順
- [`docs/publish-checklist-v1.1.0.md`](publish-checklist-v1.1.0.md) — §8 Phase 6G

---

## 3. スコープ外

- v1.1.2 tag / 新 Release
- 機能追加（Space-Track / Slack Bot 等）
- Zenn 本文の大幅改稿

---

## 4. 成功条件

1. Qiita 記事本文が `blog-draft.md` 相当（プレースホルダ「a」でない）
2. Zenn 本番まとめに Qiita URL
3. `publish-checklist-v1.1.0.md` §8 完了
4. `pytest tests/` — 60 passed

---

## 5. 関連ドキュメント

- [Phase 6F](requirements-phase6f.md) — Qiita URL・Social Preview
- [Qiita URL 正本](QIITA_PUBLISHED_URL.txt)
- [公開チェックリスト](publish-checklist-v1.1.0.md)
