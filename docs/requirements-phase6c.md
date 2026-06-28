# CAS Phase 6C — 要件定義書

**版:** 6C  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase6c.md`）

---

## 1. 概要

Phase 6A 完了後、Render Free tier へ CAS を実デプロイし、README の Live Demo URL を公開 URL に更新する。

| サブフェーズ | 内容 |
|-------------|------|
| 6C-1 | Render Blueprint デプロイ手順（ユーザー操作） |
| 6C-2 | デプロイ後スモークテスト（`/health`, `/app/`） |
| 6C-3 | README Live Demo URL + バッジ更新 |
| 6C-4 | 公開チェックリスト・deploy-cloud 追記 |

---

## 2. 機能要件

### FR-P6C-1: Render デプロイ

- [`render.yaml`](../render.yaml) — Free tier Blueprint（disk なし）
- [`docs/deploy-render-phase6c.md`](deploy-render-phase6c.md) — 実行手順
- Render Dashboard で GitHub `main` からデプロイ

### FR-P6C-2: スモークテスト

- [`backend/cli/verify_deploy.py`](../backend/cli/verify_deploy.py) — リモート `/health` + `/app/` 検証
- 手動: **デモ TLE 読込 → 接近解析**（cold start 後）

### FR-P6C-3: README Live Demo

- Live Demo セクションに実 URL 直リンク
- optional Live Demo バッジ（Render）
- 2 分デモはローカル向けとして維持

### FR-P6C-4: ドキュメント追記

- [`docs/deploy-cloud.md`](deploy-cloud.md) — Phase 6C 実 URL 例
- [`docs/publish-checklist-v1.1.0.md`](publish-checklist-v1.1.0.md) — セクション 6 完了

---

## 3. スコープ外

- Fly.io 実デプロイ
- Render Starter+ 永続 disk
- GitHub Actions 自動デプロイ → **Phase 6B**
- Space-Track / Webhook secrets 設定

---

## 4. 成功条件

1. `https://<service>.onrender.com/health` → `{"status":"ok",...}`
2. `https://<service>.onrender.com/app/` で UI 表示
3. デモ TLE → 接近解析が cold start 後に成功
4. README Live Demo が実 URL を指す
5. `pytest tests/` 60 passed

---

## 5. 関連ドキュメント

- [Phase 6A](requirements-phase6a.md) — Live Demo deferred
- [Phase 5B](requirements-phase5b.md) — render.yaml / deploy-cloud
- [Render デプロイ手順](deploy-render-phase6c.md)
