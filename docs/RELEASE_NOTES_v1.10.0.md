# CAS v1.10.0 — Phase 10C COLA Sweep & Mitigation Planning

**Conjunction Alert Simulator** v1.10.0 — Δv スイープと対策計画遷移の連携。

## ハイライト

- **Phase 10C** — Ops で direction/Δv 指定、Δv スイープ、試算→対策計画
- `POST .../mitigation-sweep` — 複数試算 + best 返却
- `POST .../mitigation-plan` — preview をコメントに含め triage 遷移
- 監査 `alert.mitigation_sweep` / `alert.mitigation_plan`

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 10C 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase10c.md |

## 使い方

Ops タブ → アラート行で direction/Δv を指定 → **回避試算** または **Δv スイープ** → **試算→対策計画**（acknowledged 時）。

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [v1.9.0 — Phase 10B SLA Metrics](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.9.0)

**License:** MIT
