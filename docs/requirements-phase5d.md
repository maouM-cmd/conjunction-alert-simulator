# CAS Phase 5D — 要件定義書

**版:** 5D  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase5d.md`）

---

## 1. 概要

Phase 5C 完了後、ポートフォリオ向けデモ品質を Phase 5 機能に合わせて刷新する。v1.1.0 リリース（Phase 5E）とセットで ship。

| サブフェーズ | 内容 |
|-------------|------|
| 5D-1 | find_demo_pair Advanced Pc + Pc メタ |
| 5D-2 | generate_demo_assets Phase 5 + PNG/GIF 再生成 |
| 5D-3 | blog-zenn / demo README 更新 |

---

## 2. 機能要件

### FR-P5D-1: デモペア

- [`find_demo_pair.py`](../backend/cli/find_demo_pair.py) — `use_advanced_pc=True`、`demo-pair.json` に `pc` / `pc_alfriend` / `pc_method_used`
- [`example.cdm`](../samples/example.cdm) — TCA / miss / Pc を demo-pair と同期

### FR-P5D-2: デモ素材

- [`generate_demo_assets.py`](../backend/cli/generate_demo_assets.py) — Phase 5 表記、`apply_cdm_covariance` API 呼び出し
- `docs/demo/*.png`, `demo.gif`, `assets-meta.json`

### FR-P5D-3: 原稿

- [`blog-zenn.md`](demo/blog-zenn.md) — Phase 5B/5C、v1.1.0

---

## 3. スコープ外

- Cesium 実画面 GIF 自動キャプチャ
- Render Live Demo URL 更新

---

## 4. 成功条件

1. `demo-pair.json` に Pc メタ
2. Phase 5 デモ PNG/GIF コミット
3. Zenn 原稿 Phase 5 反映

---

## 5. 関連ドキュメント

- [Phase 5E Release Notes](RELEASE_NOTES_v1.1.0.md)
- [Phase 5C](requirements-phase5c.md)
