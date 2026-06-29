# CAS v1.19.0 — Phase 10L PagerDuty Integration

**Conjunction Alert Simulator** v1.19.0 — PagerDuty Events API v2 による商用エスカレーション通知。

## ハイライト

- **Phase 10L** — `ALERT_WEBHOOK_FORMAT=pagerduty`
- `PAGERDUTY_ROUTING_KEY` のみで設定（URL 不要）
- 既存通知経路すべて対応（new alert / Pc escalation / mitigation / test ping）
- severity マッピング（critical / error / warning / info）

## 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `ALERT_WEBHOOK_FORMAT` | `generic` | `pagerduty` を指定 |
| `PAGERDUTY_ROUTING_KEY` | — | Events API v2 routing key |

## リンク

| | |
|--|--|
| Live Demo | https://conjunction-alert-simulator.onrender.com/app/ |
| GitHub | https://github.com/maouM-cmd/conjunction-alert-simulator |
| Phase 10L 要件 | https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/docs/requirements-phase10l.md |

## 使い方

```env
ALERT_WEBHOOK_FORMAT=pagerduty
PAGERDUTY_ROUTING_KEY=your-routing-key
```

`POST /api/v1/alerts/webhook/test` で接続確認。`/health` の `alert_delivery_format` で `pagerduty` を確認。

## ドキュメント

- [README](https://github.com/maouM-cmd/conjunction-alert-simulator/blob/main/README.md)
- [v1.18.0 — Phase 10K Covariance Propagation](https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.18.0)

**License:** MIT
