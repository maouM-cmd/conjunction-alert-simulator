# CAS Phase 10AD — 要件定義書

**版:** 10AD  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10ad.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第三十フェーズ。10AC でスコープ外とした管理者横断 breach 履歴と retention purge を実装する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `list_all_history`、`purge_old_breach_history` |
| Celery | 日次 `purge_old_breach_history` beat タスク |
| API | `GET history` で `fleet_id` 省略（管理者） |
| UI | 全艦隊履歴テーブル + CSV ダウンロード |
| env | `ALERTMANAGER_BREACH_HISTORY_RETENTION_DAYS` |

---

## 2. 機能要件

### FR-10AD-1: 管理者横断 breach 履歴

- `GET breach-states/history`（`fleet_id` 省略）— 管理者のみ
- 応答に `fleet_id` / `fleet_name` を含む
- CSV に `fleet_name` 列

### FR-10AD-2: retention purge

- `ALERTMANAGER_BREACH_HISTORY_RETENTION_DAYS`（default 90）
- Celery beat 日次 purge — `created_at` が retention 超過の行を削除
- history OFF 時は no-op

### FR-10AD-3: Ops UI

- 管理者: 全艦隊 breach 履歴テーブル
- CSV ダウンロード（横断）
- 艦隊未選択時も表示可

---

## 3. スコープ外

- breaching-only の Prometheus / Alertmanager 連携
- 履歴の source / breaching フィルタ
- per-fleet retention 設定

---

## 4. 成功条件

1. 管理者横断履歴 API + CSV が動作
2. retention purge が古い行のみ削除
3. Ops UI 反映
4. pytest 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 10AC](requirements-phase10ac.md)
