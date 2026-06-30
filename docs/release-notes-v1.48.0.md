# Release v1.48.0 — Phase 10AO

**日付:** 2026-06-28

## 概要

fleet summary offset UI、reload 履歴 Redis stale 物理 purge、dry-run CSV changes_only フィルタ。

## Added

- Ops fleet summary 前へ/次へ + `offset` 連携
- reload 履歴 Redis LIST から TTL 超過エントリを物理 purge
- `POST import?dry_run=true&changes_only=true` + dry-run CSV チェックボックス連携
