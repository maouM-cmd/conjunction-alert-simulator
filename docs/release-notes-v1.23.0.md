# Release v1.23.0 — Phase 10P

**日付:** 2026-06-28

## 概要

PagerDuty インシデント webhook を受信し、`dedup_key=cas-alert-{alert_id}` から CAS アラート状態を逆同期。10O（CAS→PD）と合わせて双方向 lifecycle を完成。

## 変更

- `PAGERDUTY_INBOUND_SYNC_ENABLED=true` + `PAGERDUTY_WEBHOOK_SIGNING_SECRET` で有効化
- `incident.acknowledged` → `acknowledged`、`incident.resolved` → `closed`（必要時 ack 連鎖）
- inbound 経路では 10O outbound を抑止（ループ防止）
- API Key 不要、署名検証のみ

## テスト

255 passed

## 関連

- [requirements-phase10p.md](requirements-phase10p.md)
