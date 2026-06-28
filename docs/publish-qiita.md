# Qiita 投稿手順

CAS 技術記事 [`docs/demo/blog-draft.md`](demo/blog-draft.md)（Qiita 転用版）の投稿チェックリストです。

Zenn 正本: https://zenn.dev/hukuhukuchan/articles/6bd364012c6bf5

---

## 事前確認

- [x] GitHub `main` に最新コミットが push 済み（画像 raw URL が有効）
- [x] [`blog-draft.md`](demo/blog-draft.md) の Live Demo / Zenn リンクが有効
- [x] ローカルで `pytest tests/` が PASS

---

## API 投稿（任意 — Phase 6F）

Personal access token がある場合:

```powershell
$env:QIITA_ACCESS_TOKEN = "<your-token>"
.\scripts\publish_qiita_item.ps1
```

成功時 `docs/QIITA_PUBLISHED_URL.txt` に URL が保存されます。

---

## 投稿手順

1. [Qiita](https://qiita.com/) にログイン
2. **新規記事** → Markdown エディタ
3. `blog-draft.md` をコピペ（タイトルは記事タイトル欄に設定）
4. プレビューで以下を確認:
   - [x] デモ GIF が表示される
   - [x] 接近一覧・CDM 比較スクリーンショットが表示される
   - [x] Live Demo / Zenn リンクが有効
5. **タグ** 例: `Python`, `FastAPI`, `宇宙`, `OSS`, `Docker`, `SGP4`
6. **公開** — https://qiita.com/maouM-cmd/items/986e533b16b348f7d5e4

---

## 公開後

- [x] README「技術記事」表に Qiita 行を追記
- [x] `blog-zenn.md` / `blog-draft.md` に Qiita URL 追記
- [x] [`publish-checklist-v1.1.0.md`](publish-checklist-v1.1.0.md) §7 Qiita を `[x]`
- [ ] Zenn 本番記事 Web エディタで Qiita 相互リンク（任意）

**Qiita URL 正本:** [`QIITA_PUBLISHED_URL.txt`](QIITA_PUBLISHED_URL.txt)

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
