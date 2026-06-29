# CAS Phase 9D — 要件定義書

**版:** 9D  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase9d.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 9 第四フェーズ。`MAX_SATELLITES=25` 壁を突破し、1,000+ 衛星の定期スクリーニングと worker 水平スケールを可能にする。

| 変更箇所 | 内容 |
|---------|------|
| チャンク | 50 sat/job Celery タスク |
| 艦隊上限 | 10,000（`FLEET_MAX_SATELLITES`） |
| CDM | Redis 共有レートリミット |
| 監視 | `GET /metrics` Prometheus |

---

## 2. 機能要件

### FR-9D-1: 艦隊 10k + チャンク

- `FLEET_MAX_SATELLITES=10000`
- `SCREENING_CHUNK_SIZE=50` — 親 run が N チャンクに分割

### FR-9D-2: Worker スケール

- `CELERY_WORKER_CONCURRENCY`、`docker compose --scale worker=N`
- `SCREENING_MAX_WORKERS` — chunk 内 ProcessPool

### FR-9D-3: 高度プリフィルタ

- worker スクリーニング default ON（既存維持）

### FR-9D-4: Space-Track CDM レートリミット

- Redis 共有 1 req/sec（マルチ worker）

### FR-9D-5: Prometheus

- `/metrics`: open alerts、screening runs、queue depth

---

## 3. スコープ外

- ad-hoc batch 25 上限（API 互換）
- API Key / `/health` 拡張（9E）

---

## 4. 成功条件

1. 51+ 衛星艦隊が 2+ チャンクで完了
2. `/metrics` 200
3. pytest 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 9C](requirements-phase9c.md)
- [商用運用ロードマップ](requirements-commercial-ops.md)
