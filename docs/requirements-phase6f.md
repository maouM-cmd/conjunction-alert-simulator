# CAS Phase 6F — 要件定義書

**版:** 6F  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase6f.md`）

---

## 1. 概要

Phase 6E（v1.1.1・CI 最適化）完了後、残る公開タスクを完結させる。Qiita 投稿、GitHub Social Preview 設定、README / Zenn 相互リンク更新。

| サブフェーズ | 内容 |
|-------------|------|
| 6F-1 | Qiita 投稿（`blog-draft.md` → 公開 URL） |
| 6F-2 | GitHub Social Preview（Settings アップロード） |
| 6F-3 | README / Zenn / チェックリスト相互リンク更新 |
| 6F-4 | docs commit / push（tag 新設なし） |

---

## 2. 機能要件

### FR-P6F-1: Qiita 公開

- [`docs/demo/blog-draft.md`](demo/blog-draft.md) を Qiita に投稿
- [`docs/publish-qiita.md`](publish-qiita.md) — 手順・公開後チェックリスト

### FR-P6F-2: Social Preview

- [`.github/social-preview.png`](../.github/social-preview.png) を GitHub Settings にアップロード
- [`docs/publish-github-social-preview.md`](publish-github-social-preview.md)

### FR-P6F-3: 相互リンク

- [`README.md`](../README.md) — 技術記事表に Qiita URL、冒頭 v1.1.1 サマリ
- [`docs/demo/blog-zenn.md`](demo/blog-zenn.md) — まとめに Qiita 相互リンク + v1.1.1
- [`docs/publish-checklist-v1.1.0.md`](publish-checklist-v1.1.0.md) — §7 完了

---

## 3. スコープ外

- v1.1.2 tag / 新 Release
- 機能追加（Space-Track / Slack Bot 等）
- Zenn 本文の大幅改稿

---

## 4. 成功条件

1. Qiita 公開 URL が README「技術記事」表に記載
2. Social Preview が GitHub Settings に設定
3. `publish-checklist-v1.1.0.md` §7 全項目完了
4. `pytest tests/` — 60 passed

---

## 5. 関連ドキュメント

- [Phase 6E](requirements-phase6e.md) — 原稿・素材・v1.1.1
- [Zenn 原稿](demo/blog-zenn.md)
- [公開チェックリスト](publish-checklist-v1.1.0.md)
