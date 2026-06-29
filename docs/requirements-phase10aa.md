# CAS Phase 10AA — 要件定義書

**版:** 10AA  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10aa.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第二十七フェーズ。10Z でスコープ外とした breach 横断一覧と手動上書きを実装する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `list_all_fleet_breach_states`、`breach_manual_override_enabled` |
| API | `GET` 管理者横断、`PUT` 手動上書き |
| UI | 全艦隊テーブル + 手動上書きボタン |
| env | `ALERTMANAGER_BREACH_STATE_MANUAL_OVERRIDE_ENABLED` |

---

## 2. 機能要件

### FR-10AA-1: 管理者横断 breach 一覧

- `GET /ops/prometheus/alertmanager/breach-states`（`fleet_id` 省略）— 管理者のみ
- active 艦隊 × 2 alertname の状態を返す

### FR-10AA-2: breach 手動上書き（opt-in）

- `PUT /ops/prometheus/alertmanager/breach-states` — fleet スコープ認可
- 監査 `alert.breach_state_manual_override`
- 次回 `sync_breaches` で実メトリクスに基づき上書きされる（リカバリ / テスト用途）

### FR-10AA-3: Ops UI

- 管理者: 全艦隊 breach テーブル
- 手動上書き ON 時: 単艦隊テーブルに breaching / ok ボタン

---

## 3. スコープ外

- sticky override（sync から保護）
- breach 変更履歴テーブル
- breaching-only フィルタ / CSV export

---

## 4. 成功条件

1. 管理者横断一覧 API が動作
2. opt-in 手動上書き + 監査が動作
3. Ops UI 反映
4. pytest 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 10Z](requirements-phase10z.md)
