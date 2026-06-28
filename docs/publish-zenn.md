# Zenn 投稿手順

CAS 技術記事 [`docs/demo/blog-zenn.md`](demo/blog-zenn.md)（**v1.2.2 / Phase 8 版**）を Zenn に公開・更新するチェックリストです。

マスター実行順: [`publish-checklist-v1.1.0.md`](publish-checklist-v1.1.0.md)  
GitHub Release 手順: [`publish-github-release.md`](publish-github-release.md)

---

## 事前確認

- [ ] GitHub `main` に最新コミットが push 済み（画像 raw URL が有効）
- [ ] tag `v1.2.2` が remote に存在
- [ ] （推奨）[GitHub Release v1.2.2](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.2.2) 公開済み
- [ ] ローカルで `pytest tests/` が PASS
- [ ] [`blog-zenn.md`](demo/blog-zenn.md) の画像 URL が `raw.githubusercontent.com` を指している

---

## 投稿・更新手順

1. [Zenn](https://zenn.dev/) にログイン
2. 既存記事を編集 — https://zenn.dev/hukuhukuchan/articles/6bd364012c6bf5/edit
3. `blog-zenn.md` の **frontmatter 以降** をコピー（`---` ブロックは Zenn UI でタイトル等を設定する場合は省略可）
4. プレビューで以下を確認:
   - [ ] **Live Demo** リンク（https://conjunction-alert-simulator.onrender.com/app/）が有効
   - [ ] デモ GIF が表示される
   - [ ] 接近一覧（Advanced Pc）スクリーンショットが表示される
   - [ ] CDM 比較スクリーンショットが表示される
   - [ ] **Phase 7 で追加したこと** 節（7C / 7A / 7B）
   - [ ] **Phase 8 で追加したこと** 節（8A / 8A-ext / 8B SMTP）
   - [ ] Webhook / Docker / 2 分デモのコードブロックが崩れていない
   - [ ] 末尾の Release v1.2.2 リンクが有効
   - [ ] Qiita 相互リンク（まとめ節）
5. **トピック** を設定: `Python`, `FastAPI`, `宇宙`, `OSS`, `Docker`, `SGP4`
6. **更新** → URL を控える

---

## 公開後

1. [`blog-zenn.md`](demo/blog-zenn.md) の frontmatter を `published: true` に更新（未設定時）
2. commit / push（原稿変更時）
3. GitHub リポ **About** → Website に Zenn URL を設定（[`publish-github-about.md`](publish-github-about.md) 参照）
4. [GitHub Issues](https://github.com/maouM-cmd/conjunction-alert-simulator/issues) でフィードバックを受け付ける旨は記事末尾に記載済み

---

## Qiita 転用

[`blog-draft.md`](demo/blog-draft.md) を使用。v1.2.2 同期済み。更新手順: [`publish-qiita.md`](publish-qiita.md)

---

## 画像 raw URL 一覧

| ファイル | URL |
|---------|-----|
| demo.gif | `https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/demo.gif` |
| 02-conjunctions.png | `https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/02-conjunctions.png` |
| 05-cdm-compare.png | `https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/05-cdm-compare.png` |
