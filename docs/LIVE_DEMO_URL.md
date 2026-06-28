# Live Demo URL (Phase 6C)

**Status:** live

| 項目 | 値 |
|------|-----|
| Base URL | `https://conjunction-alert-simulator.onrender.com` |
| App URL | **https://conjunction-alert-simulator.onrender.com/app/** |
| Render Blueprint | `exs-d90a845aeets73dssga0` |

## 検証

```powershell
venv\Scripts\python -m backend.cli.verify_deploy --url https://conjunction-alert-simulator.onrender.com
```

最終確認: 2026-06-28 — `/health` + `/app/` OK

## Cold start（Render Free tier）

初回アクセスまたは一定時間アイドル後、**30〜60 秒**ほど API 起動に時間がかかることがあります。UI は `/health` が応答するまで「サーバー起動中…」と表示します。

**推奨操作順:**

1. ページ読込 → ステータスが「準備完了」になるまで待つ
2. **デモ TLE 読込** → **高度帯プリフィルタ** ON（デフォルト）→ **高精度 Pc** ON
3. **接近解析**（閾値 50 km）→ イベント選択 → 3D 表示
