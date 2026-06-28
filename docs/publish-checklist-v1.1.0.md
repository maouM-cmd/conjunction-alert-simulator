# CAS v1.1.0 公開チェックリスト

ポートフォリオ公開の実行順（Phase 6A）。上から順にチェックしてください。

---

## 1. リポ準備（Agent 完了済み想定）

- [x] tag `v1.1.0` push 済み
- [x] [`RELEASE_NOTES_v1.1.0.md`](RELEASE_NOTES_v1.1.0.md) 作成済み
- [x] [`blog-zenn.md`](demo/blog-zenn.md) Phase 5 反映済み
- [ ] Phase 6A ドキュメント commit / push 済み

---

## 2. GitHub Release

手順: [`publish-github-release.md`](publish-github-release.md)

- [ ] `gh release create v1.1.0 --title "CAS v1.1.0 — Phase 5" --notes-file docs/RELEASE_NOTES_v1.1.0.md`
- [ ] Release ページで demo.gif が表示される
- [ ] （任意）v1.0.0 Release も未作成なら同手順で作成

---

## 3. Zenn 投稿

手順: [`publish-zenn.md`](publish-zenn.md)

- [ ] `blog-zenn.md` を Zenn にインポート / 貼り付け
- [ ] Phase 5 節（5B クラウド / 5C Webhook・CDM σ）プレビュー OK
- [ ] トピック: `Python`, `FastAPI`, `宇宙`, `OSS`, `Docker`, `SGP4`
- [ ] **公開** → 記事 URL を控える

---

## 4. README 更新（Zenn 公開後）

- [ ] [`README.md`](../README.md) の「技術記事」欄に Zenn URL を追記
- [ ] [`blog-zenn.md`](demo/blog-zenn.md) の frontmatter `published: true` に変更
- [ ] commit / push

---

## 5. GitHub リポ About

Settings → General → **About**（またはリポ右上 ⚙️ About）

| 項目 | 推奨値 |
|------|--------|
| Description | `TLE-based satellite conjunction simulator — SGP4, Pc, CDM, CesiumJS, FastAPI` |
| Website | Zenn 記事 URL（または Release URL） |
| Topics | `satellite`, `conjunction`, `sgp4`, `fastapi`, `cesium`, `space-debris`, `python` |

- [ ] Description 設定
- [ ] Topics 設定
- [ ] Website に Zenn URL（公開後）

---

## 6. 後回し（Phase 6C）

- [ ] Render / Fly.io デプロイ
- [ ] README Live Demo URL 追記

---

## 関連リンク

| 用途 | URL |
|------|-----|
| リポ | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Release v1.1.0 | https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.1.0 |
| Issues | https://github.com/maouM-cmd/conjunction-alert-simulator/issues |
