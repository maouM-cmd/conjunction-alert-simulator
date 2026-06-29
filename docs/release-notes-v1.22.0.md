# Release v1.22.0 — Phase 10O

**日付:** 2026-06-28

## 概要

PagerDuty Events API v2 の acknowledge / resolve を CAS アラート状態遷移と連動。安定 `dedup_key=cas-alert-{alert_id}` でインシデントライフサイクルを閉じる。

## 変更

- `PAGERDUTY_LIFECYCLE_ENABLED=true` + `ALERT_WEBHOOK_FORMAT=pagerduty` で lifecycle 有効
- 新規 screening アラート: per-alert `trigger` + `dedup_key`
- Ops `acknowledged` → `acknowledge`、`closed` / `false_positive` → `resolve`
- escalation / mitigation の dedup_key を `cas-alert-*` に統一（旧 `cas-escalation-*` 置換）
- lifecycle OFF 時は Phase 10L バッチ挙動維持

## テスト

247 passed

## 関連

- [requirements-phase10o.md](requirements-phase10o.md)
