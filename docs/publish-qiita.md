# Qiita 投稿手順

CAS 技術記事 [`docs/demo/blog-draft.md`](demo/blog-draft.md)（Qiita 転用版）の投稿チェックリストです。

Zenn 正本: https://zenn.dev/hukuhukuchan/articles/6bd364012c6bf5

---

## 事前確認

- [x] GitHub `main` に最新コミットが push 済み（画像 raw URL が有効）
- [x] [`blog-draft.md`](demo/blog-draft.md) の Live Demo / Zenn リンクが有効
- [x] ローカルで `pytest tests/` が PASS

---

## API 投稿・更新（Phase 6F / 6G）

Personal access token は https://qiita.com/settings/applications で発行。**スコープに「記事の作成・更新」（write）を含める**こと（read のみだと PATCH が `403 Forbidden`）。

### 新規投稿

```powershell
$env:QIITA_ACCESS_TOKEN = "<write スコープ付き token>"
.\scripts\publish_qiita_item.ps1
```

### 既存記事更新（Phase 6G）

Item ID: `986e533b16b348f7d5e4` — 正本 [`QIITA_PUBLISHED_URL.txt`](QIITA_PUBLISHED_URL.txt)

```powershell
$env:QIITA_ACCESS_TOKEN = "<write スコープ付き token>"
.\scripts\publish_qiita_item.ps1 -Update
```

成功時、本文・タグが [`blog-draft.md`](demo/blog-draft.md) 相当に上書きされます。

### ブラウザ更新（トークンなし / write 不可時）

1. https://qiita.com/maouM-cmd/items/986e533b16b348f7d5e4/edit
2. 本文を `blog-draft.md` で置換（先頭 `# タイトル` 行はタイトル欄へ）
3. タグ: `Python`, `FastAPI`, `宇宙`, `OSS`, `Docker`, `SGP4` → **更新**

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
- [ ] Zenn 本番記事 Web エディタで Qiita 相互リンク — https://zenn.dev/hukuhukuchan/articles/6bd364012c6bf5/edit（[`blog-zenn.md`](demo/blog-zenn.md) まとめ節）

**Qiita URL 正本:** [`QIITA_PUBLISHED_URL.txt`](QIITA_PUBLISHED_URL.txt)

---

## 既存記事更新（Phase 6G）

- [ ] Qiita 本文・タグ差し替え（`publish_qiita_item.ps1 -Update` またはブラウザ編集）
- [ ] 記事プレビューで GIF / PNG / リンク確認

---

## 既存記事更新（Phase 6G-ext — v1.2.2 同期）

Phase 6G スキップ分の再開。[`blog-draft.md`](demo/blog-draft.md) が Phase 7/8/8B + v1.2.2 まとめに更新された後:

```powershell
cd C:\Users\admin\OneDrive\ドキュメント\conjunction-alert-simulator
.\scripts\publish_qiita_item.ps1 -DryRun -Update   # 本文長・Item ID 確認
$env:QIITA_ACCESS_TOKEN = "<write スコープ付き token>"
.\scripts\publish_qiita_item.ps1 -Update
```

- [ ] `blog-draft.md` が v1.2.2 相当（Phase 7/8/8B 含む）
- [ ] DryRun または API 更新成功
- [ ] 記事プレビューで Phase 8 / SMTP 節を確認
- [ ] Release リンクが v1.2.2

### 403 Forbidden（read トークン）

`.qiita-token.local` または環境変数の token が **read のみ** の場合、PATCH は 403 になる。

1. https://qiita.com/settings/applications で **write スコープ**付き token を再発行
2. `$env:QIITA_ACCESS_TOKEN = "<新 token>"` を設定（`.qiita-token.local` を上書きしても可）
3. `.\scripts\publish_qiita_item.ps1 -Update` を再実行

本番記事がプレースホルダ「a」のままの場合は、上記または [ブラウザ更新](#ブラウザ更新トークンなし--write-不可時) を実施。

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
