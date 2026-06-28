# Zenn 投稿手順

CAS 技術記事 [`docs/demo/blog-zenn.md`](demo/blog-zenn.md)（**v1.1.0 / Phase 5 版**）を Zenn に公開するチェックリストです。

マスター実行順: [`publish-checklist-v1.1.0.md`](publish-checklist-v1.1.0.md)  
GitHub Release 手順: [`publish-github-release.md`](publish-github-release.md)

---

## 事前確認

- [ ] GitHub `main` に最新コミットが push 済み（画像 raw URL が有効）
- [ ] tag `v1.1.0` が remote に存在
- [ ] （推奨）[GitHub Release v1.1.0](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.1.0) 公開済み
- [ ] ローカルで `pytest tests/` が PASS
- [ ] [`blog-zenn.md`](demo/blog-zenn.md) の画像 URL が `raw.githubusercontent.com` を指している

---

## 投稿手順

1. [Zenn](https://zenn.dev/) にログイン
2. **新規記事** → **Markdown をインポート** またはエディタに貼り付け
3. `blog-zenn.md` の **frontmatter 以降** をコピー（`---` ブロックは Zenn UI でタイトル等を設定する場合は省略可）
4. プレビューで以下を確認:
   - [ ] **Live Demo** リンク（https://conjunction-alert-simulator.onrender.com/app/）が有効
   - [ ] デモ GIF が表示される
   - [ ] 接近一覧（Advanced Pc）スクリーンショットが表示される
   - [ ] CDM 比較スクリーンショットが表示される
   - [ ] **Phase 5 で追加したこと** 節（5B クラウド / 5C Webhook・CDM σ）が崩れていない
   - [ ] Webhook / Docker / 2 分デモのコードブロックが崩れていない
   - [ ] 末尾の Release v1.1.0 リンクが有効
5. **トピック** を設定: `Python`, `FastAPI`, `宇宙`, `OSS`, `Docker`, `SGP4`
6. **公開** → URL を控える

---

## 公開後

1. [`README.md`](../README.md) の **「技術記事」** 欄に Zenn URL を追記（「準備中」を置き換え）
2. [`blog-zenn.md`](demo/blog-zenn.md) の frontmatter を `published: true` に更新
3. commit / push
4. GitHub リポ **About** → Website に Zenn URL を設定（[`publish-github-about.md`](publish-github-about.md) 参照。Zenn 公開前は Live Demo URL でも可）
5. [GitHub Issues](https://github.com/maouM-cmd/conjunction-alert-simulator/issues) でフィードバックを受け付ける旨は記事末尾に記載済み

---

## Qiita 転用

[`blog-draft.md`](demo/blog-draft.md) を使用。画像は同じ raw URL 形式に統一済み。Phase 5 節は [`blog-zenn.md`](demo/blog-zenn.md) から転用可。

---

## 画像 raw URL 一覧

| ファイル | URL |
|---------|-----|
| demo.gif | `https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/demo.gif` |
| 02-conjunctions.png | `https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/02-conjunctions.png` |
| 05-cdm-compare.png | `https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/05-cdm-compare.png` |
