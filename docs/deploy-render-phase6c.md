# Phase 6C — Render 実デプロイ手順

**対象:** Free tier Blueprint — [`render.yaml`](../render.yaml)

詳細・トラブルシュート: [deploy-cloud.md](deploy-cloud.md#render)

---

## 1. Blueprint デプロイ

1. [Render Dashboard](https://dashboard.render.com/) にログイン
2. **New** → **Blueprint**
3. GitHub リポ `maouM-cmd/conjunction-alert-simulator` を接続（未接続なら authorize）
4. ブランチ **main**、`render.yaml` 内容を確認
5. **Apply** → 初回 Docker ビルド完了まで待機（5〜10 分）
6. Web Service の **URL** を控える（例: `https://conjunction-alert-simulator.onrender.com`）

README の **Deploy to Render** ボタンからも開始可。

---

## 2. スモークテスト

```powershell
cd C:\Users\admin\OneDrive\ドキュメント\conjunction-alert-simulator
venv\Scripts\python -m backend.cli.verify_deploy --url https://<your-service>.onrender.com
```

手動:

```powershell
curl https://<your-service>.onrender.com/health
```

ブラウザ: `https://<your-service>.onrender.com/app/`

1. **デモ TLE 読込** → **高精度 Pc** ON → **接近解析**（閾値 50 km）
2. cold start 直後は 30〜60 秒待つ。504 の場合は再試行

---

## 3. デプロイ後（リポ更新）

URL 確定後、Agent / 手動で以下を更新:

- [`README.md`](../README.md) — Live Demo 直リンク
- [`docs/deploy-cloud.md`](deploy-cloud.md) — 実 URL 例
- [`docs/publish-checklist-v1.1.0.md`](publish-checklist-v1.1.0.md) — セクション 6 チェック

---

## Free tier 注意

| 項目 | 内容 |
|------|------|
| スリープ | 非アクセス時スリープ → 初回アクセスで cold start |
| ディスク | 永続 disk 不可 — TLE キャッシュは再起動で消える |
| 初回解析 | CelesTrak 取得のため 30〜90 秒かかることがある |
| 閾値 | 50 km 推奨（504 回避） |

---

## 関連

- [Phase 6C 要件](requirements-phase6c.md)
- [公開チェックリスト v1.1.0](publish-checklist-v1.1.0.md)
