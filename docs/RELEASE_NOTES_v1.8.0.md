# CAS v1.8.0 — Phase 10A Alert-Linked COLA Preview

**Conjunction Alert Simulator** v1.8.0 — 永続化アラートから回避試算（COLA preview）を実行・記録。

## ハイライト

- **Phase 10A** — Ops アラートから maneuver preview をワンクリック実行
- 試算結果を `alert_mitigation_previews` に永続化（履歴複数件）
- `POST/GET .../mitigation-preview(s)` API
- 監査ログ `alert.mitigation_preview`
- Ops UI「回避試算」ボタン + before/after miss 距離表示

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 10A 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase10a.md |

## 使い方

Ops タブで艦隊を選択 → アラート行の **回避試算** をクリック。デフォルト: prograde Δv 0.01 m/s。

```powershell
curl -X POST http://localhost:8000/api/v1/ops/alerts/{alert_id}/mitigation-preview `
  -H "Content-Type: application/json" `
  -d '{"direction":"prograde","delta_v_ms":0.01}'
```

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [v1.7.0 — Phase 9E Platform Baseline](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.7.0)

**License:** MIT
