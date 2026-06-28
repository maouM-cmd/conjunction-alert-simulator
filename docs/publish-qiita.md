# Qiita 投稿手順

CAS 技術記事 [`docs/demo/blog-draft.md`](demo/blog-draft.md)（Qiita 転用版）の投稿チェックリストです。

Zenn 正本: https://zenn.dev/hukuhukuchan/articles/6bd364012c6bf5

---

## 事前確認

- [ ] GitHub `main` に最新コミットが push 済み（画像 raw URL が有効）
- [ ] [`blog-draft.md`](demo/blog-draft.md) の Live Demo / Zenn リンクが有効
- [ ] ローカルで `pytest tests/` が PASS

---

## 投稿手順

1. [Qiita](https://qiita.com/) にログイン
2. **新規記事** → Markdown エディタ
3. `blog-draft.md` をコピペ（タイトルは記事タイトル欄に設定）
4. プレビューで以下を確認:
   - [ ] デモ GIF が表示される
   - [ ] 接近一覧・CDM 比較スクリーンショットが表示される
   - [ ] Live Demo / Zenn リンクが有効
5. **タグ** 例: `Python`, `FastAPI`, `宇宙`, `OSS`, `Docker`, `SGP4`
6. **公開** → URL を控える

---

## 公開後（任意）

- README「技術記事」表に Qiita 行を追記
- Zenn 記事末尾に Qiita URL を追記（相互リンク）

---

## 画像 raw URL 一覧

| ファイル | URL |
|---------|-----|
| demo.gif | `https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/demo.gif` |
| 02-conjunctions.png | `https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/02-conjunctions.png` |
| 05-cdm-compare.png | `https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/05-cdm-compare.png` |

---

## 関連

- [Zenn 投稿手順](publish-zenn.md)
- [公開チェックリスト v1.1.0](publish-checklist-v1.1.0.md)
