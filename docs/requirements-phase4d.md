# CAS Phase 4D — 要件定義書

**版:** 4D  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase4d.md`）

---

## 1. 概要

Phase 4B-Ext 完了後、ポートフォリオ公開可能な状態に仕上げる。デモ素材再生成、技術ブログ更新、README/UI 整備を行う。

| サブフェーズ | 内容 |
|-------------|------|
| 4D-0 | 4B-Ext push（先行） |
| 4D-1 | デモ PNG/GIF 再生成 |
| 4D-2 | 技術ブログ Phase 4 版 |
| 4D-3 | README / UI サブタイトル |
| 4D-4 | テスト + ship |

---

## 2. 機能要件

### FR-P4D-1: デモ素材

- [`generate_demo_assets.py`](../backend/cli/generate_demo_assets.py) 拡張
- 出力: `01-initial.png` 〜 `05-cdm-compare.png`, `demo.gif`
- Advanced Pc + CDM compare を API から取得して描画

### FR-P4D-2: 技術ブログ

- [`docs/demo/blog-draft.md`](demo/blog-draft.md) / [`blog-zenn.md`](demo/blog-zenn.md) を Phase 4 完成版に更新
- Phase 2〜4 の Pc 進化、Docker、Webhook、Space-Track を記載

### FR-P4D-3: README / UI

- README デモセクションに `05-cdm-compare.png` 追加
- [`frontend/index.html`](../frontend/index.html) サブタイトル Phase 4 対応

### FR-P4D-4: 品質

- `docs/demo/demo.gif` 存在チェック（README リンク切れ防止）
- `pytest tests/` 全件 PASS

---

## 3. スコープ外

- Zenn / Qiita への実投稿 → **Phase 5A で原稿・手順対応済み**（[`requirements-phase5a.md`](requirements-phase5a.md)、[`publish-zenn.md`](publish-zenn.md)）
- Render / Fly.io 実デプロイ
- Cesium 実画面ブラウザ録画 GIF

---

## 4. 成功条件

1. `9b40aa5` + 4D 変更が origin/main に反映
2. `docs/demo/demo.gif` と PNG がリポに存在
3. ブログ稿が Phase 4 機能を正確に説明
4. `pytest tests/` 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 4C](requirements-phase4c.md) — 4D スコープ外 → 本フェーズで対応
- [Phase 4B-Ext](requirements-phase4b-ext.md) — 同上
- [デモ手順](demo/README.md)
