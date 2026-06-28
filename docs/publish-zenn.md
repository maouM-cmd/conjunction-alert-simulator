# Zenn 投稿手順

CAS 技術記事 [`docs/demo/blog-zenn.md`](demo/blog-zenn.md) を Zenn に公開するチェックリストです。

## 事前確認

- [ ] GitHub `main` に最新コミットが push 済み（画像 raw URL が有効）
- [ ] ローカルで `pytest tests/` が PASS
- [ ] [`blog-zenn.md`](demo/blog-zenn.md) の画像 URL が `raw.githubusercontent.com` を指している

## 投稿手順

1. [Zenn](https://zenn.dev/) にログイン
2. **新規記事** → **Markdown をインポート** またはエディタに貼り付け
3. `blog-zenn.md` の **frontmatter 以降** をコピー（`---` ブロックは Zenn UI でタイトル等を設定する場合は省略可）
4. プレビューで以下を確認:
   - [ ] デモ GIF が表示される
   - [ ] CDM 比較スクリーンショットが表示される
   - [ ] コードブロックの PowerShell コマンドが崩れていない
5. **トピック** を設定: `Python`, `FastAPI`, `宇宙`, `OSS`, `Docker`, `SGP4`
6. **公開** → URL を控える

## 公開後

1. [`README.md`](../README.md) の「技術記事」欄に Zenn URL を追記
2. GitHub リポジトリの About / Description に CAS の一行説明を設定（任意）
3. [GitHub Issues](https://github.com/maouM-cmd/conjunction-alert-simulator/issues) でフィードバックを受け付ける旨を記事末尾に記載済み

## Qiita 転用

[`blog-draft.md`](demo/blog-draft.md) を使用。画像は同じ raw URL 形式に統一済み。

## 画像 raw URL 一覧

| ファイル | URL |
|---------|-----|
| demo.gif | `https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/demo.gif` |
| 02-conjunctions.png | `https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/02-conjunctions.png` |
| 05-cdm-compare.png | `https://raw.githubusercontent.com/maouM-cmd/conjunction-alert-simulator/main/docs/demo/05-cdm-compare.png` |
