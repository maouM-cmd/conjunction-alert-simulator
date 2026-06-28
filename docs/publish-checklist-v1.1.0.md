# CAS v1.1.0 公開チェックリスト

ポートフォリオ公開の実行順（Phase 6A）。上から順にチェックしてください。

---

## 1. リポ準備（Agent 完了済み想定）

- [x] tag `v1.1.0` push 済み
- [x] [`RELEASE_NOTES_v1.1.0.md`](RELEASE_NOTES_v1.1.0.md) 作成済み
- [x] [`blog-zenn.md`](demo/blog-zenn.md) Phase 5 反映済み
- [x] Phase 6A / 6C ドキュメント commit / push 済み

---

## 2. GitHub Release

手順: [`publish-github-release.md`](publish-github-release.md)

- [x] `gh release create v1.1.0 --title "CAS v1.1.0 — Phase 5" --notes-file docs/RELEASE_NOTES_v1.1.0.md`
- [x] Release ページで demo.gif が表示される
- [x] v1.0.0 Release 作成済み

---

## 3. Zenn 投稿

手順: [`publish-zenn.md`](publish-zenn.md)

- [x] `blog-zenn.md` を Zenn にインポート / 貼り付け
- [x] Phase 5 節（5B クラウド / 5C Webhook・CDM σ）プレビュー OK
- [x] トピック: `Python`, `FastAPI`, `宇宙`, `OSS`, `Docker`, `SGP4`
- [x] **公開** — https://zenn.dev/hukuhukuchan/articles/6bd364012c6bf5

---

## 4. README 更新（Zenn 公開後）

- [x] [`README.md`](../README.md) の「技術記事」欄に Zenn URL を追記
- [x] [`blog-zenn.md`](demo/blog-zenn.md) の frontmatter `published: true` に変更
- [x] commit / push

---

## 5. GitHub リポ About

Settings → General → **About**（またはリポ右上 ⚙️ About）

| 項目 | 推奨値 |
|------|--------|
| Description | `TLE-based satellite conjunction simulator — SGP4, Pc, CDM, CesiumJS, FastAPI` |
| Website | https://zenn.dev/hukuhukuchan/articles/6bd364012c6bf5 |
| Topics | `satellite`, `conjunction`, `sgp4`, `fastapi`, `cesium`, `space-debris`, `python` |

手順: [`publish-github-about.md`](publish-github-about.md)

- [x] Description 設定
- [x] Topics 設定
- [x] Website に Zenn URL 設定済み

---

## 6. Phase 6C — Render Live Demo

手順: [`deploy-render-phase6c.md`](deploy-render-phase6c.md) | URL: [`LIVE_DEMO_URL.md`](LIVE_DEMO_URL.md)

- [x] Render Blueprint デプロイ
- [x] `verify_deploy --url https://conjunction-alert-simulator.onrender.com` PASS
- [x] `LIVE_DEMO_URL.md` + README Live Demo に App URL 追記

---

## 7. Phase 6F — 公開完結

- [x] [`.github/social-preview.png`](../.github/social-preview.png) を GitHub Settings → Social preview にアップロード — [手順](publish-github-social-preview.md)
- [x] Qiita 投稿 — https://qiita.com/maouM-cmd/items/986e533b16b348f7d5e4
- [x] v1.1.1 Release

---

## 8. Phase 6G — 公開仕上げ（スキップ — 2026-06-28）

ポートフォリオ完成度 98% のため任意タスクとして **見送り**。Phase 7 機能拡張へ移行。

- [x] ~~Qiita 本文・タグを [`blog-draft.md`](demo/blog-draft.md) 相当に更新~~ — **N/A（スキップ）**
- [x] ~~Zenn 本番まとめに Qiita リンク~~ — **N/A（スキップ）**

原稿・手順は [`publish-qiita.md`](publish-qiita.md) / [`blog-draft.md`](demo/blog-draft.md) に残置。

---

## 9. Phase 7 Ship — v1.2.0 Release

手順: [`publish-github-release.md`](publish-github-release.md) | 本文: [`RELEASE_NOTES_v1.2.0.md`](RELEASE_NOTES_v1.2.0.md)

- [ ] `pytest tests/` PASS
- [ ] `CHANGELOG.md` / README / `blog-zenn.md` Phase 7 反映 commit / push
- [ ] `git tag v1.2.0` + `git push origin v1.2.0`
- [ ] `gh release create v1.2.0 --title "CAS v1.2.0 — Phase 7" --notes-file docs/RELEASE_NOTES_v1.2.0.md`
- [ ] Release ページで demo.gif 表示確認
- [ ] （任意）Zenn 本番記事に Phase 7 節を手動追記 — [`publish-zenn.md`](publish-zenn.md)

---

## 10. Phase 8 Ship — v1.2.1 Release

手順: [`publish-github-release.md`](publish-github-release.md) | 本文: [`RELEASE_NOTES_v1.2.1.md`](RELEASE_NOTES_v1.2.1.md)

- [ ] `pytest tests/` PASS
- [ ] `CHANGELOG.md` / README / `blog-zenn.md` Phase 8 反映 commit / push
- [ ] `git tag v1.2.1` + `git push origin v1.2.1`
- [ ] `gh release create v1.2.1 --title "CAS v1.2.1 — Phase 8" --notes-file docs/RELEASE_NOTES_v1.2.1.md`
- [ ] Release ページで demo.gif 表示確認
- [ ] （任意）Zenn 本番記事に Phase 8 節を手動追記 — [`publish-zenn.md`](publish-zenn.md)

---

## 11. Phase 8B Ship — v1.2.2 Release

手順: [`publish-github-release.md`](publish-github-release.md) | 本文: [`RELEASE_NOTES_v1.2.2.md`](RELEASE_NOTES_v1.2.2.md)

- [ ] `pytest tests/` PASS
- [ ] `CHANGELOG.md` / README / `blog-zenn.md` Phase 8B 反映 commit / push
- [ ] `git tag v1.2.2` + `git push origin v1.2.2`
- [ ] `gh release create v1.2.2 --title "CAS v1.2.2 — Phase 8B" --notes-file docs/RELEASE_NOTES_v1.2.2.md`
- [ ] Release ページで demo.gif 表示確認
- [ ] （任意）Zenn 本番記事に Phase 8B 節を手動追記 — [`publish-zenn.md`](publish-zenn.md)

---

## 関連リンク

| 用途 | URL |
|------|-----|
| リポ | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| Zenn | https://zenn.dev/hukuhukuchan/articles/6bd364012c6bf5 |
| Release v1.1.1 | https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.1.1 |
| Release v1.2.0 | https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.2.0 |
| Release v1.2.1 | https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.2.1 |
| Release v1.2.2 | https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.2.2 |
| Phase 7 | [`requirements-phase7.md`](requirements-phase7.md) |
| Issues | https://github.com/maouM-cmd/conjunction-alert-simulator/issues |
