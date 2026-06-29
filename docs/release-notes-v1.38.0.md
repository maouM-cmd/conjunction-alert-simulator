# Release v1.38.0 — Phase 10AE

**日付:** 2026-06-28

## 概要

10AD でスコープ外とした breaching-only Prometheus 連携と breach 履歴フィルタを実装。ルール雛形が breach Gauge と一致し、Ops UI から履歴を絞り込み可能。

## 変更

- `GET fleet-alert-rules?breaching_only=true` — `cas_fleet_*_breach == 1` expr
- `GET history` — `source` / `breaching_only` フィルタ
- Ops UI — 履歴 source セレクト + breaching のみチェックボックス

## テスト

352 passed（+6）

## 関連

- [requirements-phase10ae.md](requirements-phase10ae.md)
