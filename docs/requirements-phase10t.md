# CAS Phase 10T — 要件定義書

**版:** 10T  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10t.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第二十フェーズ。10R/10S で先送りした STM `open` 巻き戻し（opt-in）と Alertmanager silences API を実装する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `alert_stm_service` reopen、`alertmanager_silence_service` |
| API | `POST/GET /ops/prometheus/alertmanager/silences` |
| env | `ALERT_STM_REOPEN_TO_OPEN_ENABLED`, `ALERTMANAGER_SILENCES_ENABLED` |

---

## 2. 機能要件

### FR-10T-1: STM reopen（opt-in）

- `ALERT_STM_REOPEN_TO_OPEN_ENABLED=true` 時:
  - `acknowledged` → `open`
  - `escalated` → `open`
  - `false_positive` → `open`
- `closed` / `mitigation_planned` からは不可

### FR-10T-2: Alertmanager silences

- `POST /api/v2/silences` — fleet_id (+ optional alertname) matcher
- `GET /api/v2/silences` — active silences 一覧

### FR-10T-3: Ops UI

- `open` 遷移ラベル「再オープン」

---

## 3. 環境変数

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `ALERT_STM_REOPEN_TO_OPEN_ENABLED` | `false` | opt-in |
| `ALERTMANAGER_SILENCES_ENABLED` | `false` | opt-in |
| `ALERTMANAGER_SILENCE_DEFAULT_HOURS` | `4` | 作成時 default |

---

## 4. スコープ外

- triage 時の自動 silence、`mitigation_planned`/`closed` からの reopen、Celery 定期 push

---

## 5. 成功条件

1. reopen default OFF で後方互換、ON で 3 状態から `open` へ遷移可能
2. silences API が fleet 単位で動作
3. pytest 全件 PASS

---

## 6. 関連ドキュメント

- [Phase 10S](requirements-phase10s.md)
- [Phase 10R](requirements-phase10r.md)
