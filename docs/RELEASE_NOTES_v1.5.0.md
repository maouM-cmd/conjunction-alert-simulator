# CAS v1.5.0 — Phase 9C Alert Ops

**Conjunction Alert Simulator** v1.5.0 — アラート永続化と triage ワークフロー。

## ハイライト

- **Phase 9C** — `conjunction_alerts` テーブル、screening 結果から自動 ingest
- 状態遷移: open → acknowledged → mitigation_planned → closed / false_positive
- ±24h 重複抑制、**新規 open のみ** webhook 通知
- UI **運用 Ops** タブ — 艦隊サマリ、アラート triage

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 9C 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase9c.md |

## デモ

docker compose 起動後、UI **運用 Ops** タブで艦隊を選択 → アラート一覧 → Ack / クローズ。

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [v1.4.0 — Phase 9B Screening](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.4.0)

**License:** MIT
