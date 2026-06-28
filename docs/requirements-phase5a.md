# CAS Phase 5A — 要件定義書

**版:** 5A  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase5a.md`）

---

## 1. 概要

Phase 4D 完了後、ポートフォリオ公開・訴求を整える。Zenn 投稿原稿、GitHub Release v1.0.0、README バッジ、最小 CI を追加する。

| サブフェーズ | 内容 |
|-------------|------|
| 5A-1 | CHANGELOG + Release v1.0.0 |
| 5A-2 | Zenn 原稿 raw URL 仕上げ + 投稿手順 |
| 5A-3 | README バッジ + 2 分デモ |
| 5A-4 | GitHub Actions pytest + ship |

---

## 2. 機能要件

### FR-P5A-1: Release

- [`CHANGELOG.md`](../CHANGELOG.md)
- [`docs/RELEASE_NOTES_v1.0.0.md`](RELEASE_NOTES_v1.0.0.md)
- Git tag `v1.0.0` + GitHub Release

### FR-P5A-2: Zenn 原稿

- [`docs/demo/blog-zenn.md`](demo/blog-zenn.md) — raw 画像 URL
- [`docs/publish-zenn.md`](publish-zenn.md) — 投稿チェックリスト

### FR-P5A-3: README 訴求

- shields.io バッジ（License / Python / CI / Release）
- 「2 分デモ」クイックスタート

### FR-P5A-4: CI

- [`.github/workflows/test.yml`](../.github/workflows/test.yml)

---

## 3. スコープ外

- Zenn ブラウザからの**実投稿**（手順まで）
- Render / Fly.io 常時公開デモ URL
- Slack Bot 本番連携

---

## 4. 成功条件

1. `CHANGELOG.md` + `v1.0.0` GitHub Release 公開
2. `blog-zenn.md` が raw 画像 URL 付きで Zenn に貼れる
3. README にバッジ + 2 分デモ手順
4. GitHub Actions pytest green
5. `pytest tests/` ローカル PASS

---

## 5. 関連ドキュメント

- [Phase 4D](requirements-phase4d.md) — Zenn 実投稿 → 5A 原稿・手順で対応
