# CAS Phase 10AI — 要件定義書

**版:** 10AI  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10ai.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第三十五フェーズ。10AH でスコープ外とした reload リトライ/Celery フォールバック、retention CSV、履歴日次集計を実装する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `reload_prometheus` リトライ + Celery フォールバック |
| Celery | `prometheus_reload` タスク |
| API | settings `format=csv`、`GET history/summary` |
| UI | reload queued、retention CSV、日次 summary テーブル |

---

## 2. 機能要件

### FR-10AI-1: Prometheus reload リトライ + Celery フォールバック

- `PROMETHEUS_RELOAD_MAX_RETRIES`（default 3）で同期 POST リトライ
- 全リトライ失敗かつ `PROMETHEUS_RELOAD_CELERY_FALLBACK=true` なら Celery enqueue
- `FleetAlertRulesApplyOut.reload_queued`
- 任意 `POST /ops/prometheus/reload` — 手動 reload / Celery 再実行

### FR-10AI-2: retention CSV エクスポート

- `GET /ops/fleets/breach-history-settings?format=csv`
- 列: `fleet_id,fleet_name,retention_days,effective_retention_days`

### FR-10AI-3: breach 履歴日次集計

- `GET /ops/prometheus/alertmanager/breach-states/history/summary`
- history GET と同一クエリ（fleet_id, alertnames, source, breaching_only, since, until）
- 日次バケット: `day`, `total`, `breaching_count`

### FR-10AI-4: Ops UI

- apply 後 reload queued メッセージ
- retention CSV ダウンロード
- breach history セクションに日次 summary テーブル

---

## 3. スコープ外

- summary CSV エクスポート
- retention CSV インポート
- reload Celery 結果の Ops ポーリング UI

---

## 4. 成功条件

1. reload リトライ / Celery fallback / CSV / summary API が動作
2. Ops UI 反映
3. pytest 全件 PASS（377）

---

## 5. 関連ドキュメント

- [Phase 10AH](requirements-phase10ah.md)
