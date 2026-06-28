# implementation_plan — CAS

## Phase 8B — SMTP メール通知

`ALERT_WEBHOOK_FORMAT=smtp` を [`webhook_notifier.py`](backend/app/services/webhook_notifier.py) に追加。`smtplib` で単一衛星 / batch / test ping を配信。generic / slack / slack_bot 互換維持。要件: [`docs/requirements-phase8b.md`](docs/requirements-phase8b.md)。完了後 v1.2.2 Ship または次機能。
