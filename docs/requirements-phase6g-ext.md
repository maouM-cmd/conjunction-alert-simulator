# CAS Phase 6G-ext — 要件定義書

**版:** 6G-ext  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase6g-ext.md`）

---

## 1. 概要

Phase 6G（Qiita 本文更新）スキップ後、v1.2.2 時点の公開コンテンツをポートフォリオ向けに同期する。[`blog-zenn.md`](demo/blog-zenn.md) を正本とし、Qiita 原稿 [`blog-draft.md`](demo/blog-draft.md) を Phase 7/8/8B まで追従させる。

| サブフェーズ | 内容 |
|-------------|------|
| 6G-ext-1 | `blog-draft.md` を v1.2.2 相当に更新 |
| 6G-ext-2 | Qiita Item `986e533b16b348f7d5e4` PATCH 更新（トークンあり時） |
| 6G-ext-3 | `publish-zenn.md` / `publish-qiita.md` / checklist 更新 |

---

## 2. 機能要件

### FR-P6G-ext-1: Qiita 原稿同期

- Phase 7（7C/7A/7B）、Phase 8（8A/8A-ext/8B）節を `blog-draft.md` に反映
- まとめ Release → v1.2.2
- 先頭 Zenn版 / Qiita版 相互リンクを維持

### FR-P6G-ext-2: Qiita API 更新

- [`scripts/publish_qiita_item.ps1`](../scripts/publish_qiita_item.ps1) `-Update`
- トークンなし時は repo 原稿 + 手順のみ（ブラウザ更新案内）

### FR-P6G-ext-3: 手順ドキュメント

- [`publish-zenn.md`](publish-zenn.md) — v1.2.2 プレビュー確認項目
- [`publish-checklist-v1.1.0.md`](publish-checklist-v1.1.0.md) — §12

---

## 3. スコープ外

- v1.2.3 tag / 新 GitHub Release
- 機能コード変更
- Qiita 新規投稿

---

## 4. 成功条件

1. `blog-draft.md` が Phase 7/8/8B + v1.2.2 まとめを含む
2. 投稿手順ドキュメント更新
3. `pytest tests/` 全件 PASS
4. docs commit / push 済み
5. （任意）Qiita / Zenn 本番 Web 反映

---

## 5. 関連ドキュメント

- [Phase 6G](requirements-phase6g.md) — 初回定義（スキップ）
- [Qiita 手順](publish-qiita.md)
- [Zenn 手順](publish-zenn.md)
- [implementation_plan.md](../implementation_plan.md)

---

## 6. 本番反映（6G-ext live）— 進行中

| 項目 | 状態 |
|------|------|
| Repo 原稿同期 | **完了**（`0361a5f`） |
| Qiita DryRun | **完了** |
| Qiita API `-Update` | **403** — write スコープ token 要 |
| Qiita 本番 | 本文プレースホルダ「a」のまま — ブラウザ更新待ち |
| Zenn 本番 | Web エディタ同期待ち（ログイン要） |

write スコープ token 設定後:

```powershell
$env:QIITA_ACCESS_TOKEN = "<write スコープ token>"
.\scripts\publish_qiita_item.ps1 -Update
```
