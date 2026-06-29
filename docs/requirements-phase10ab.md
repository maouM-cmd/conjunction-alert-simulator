# CAS Phase 10AB — 要件定義書

**版:** 10AB  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10ab.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第二十八フェーズ。10AA でスコープ外とした breach sticky 上書きを実装する。

| 変更箇所 | 内容 |
|---------|------|
| DB | `fleet_alert_breach_states.is_manual_sticky` |
| Service | `is_sticky_override`、`set_sticky_override`、`sync_breaches` スキップ |
| API | `PUT` sticky フラグ、`DELETE .../sticky` |
| UI | sticky バッジ + 自動同期ボタン |
| env | `ALERTMANAGER_BREACH_STATE_STICKY_OVERRIDE_ENABLED` |

---

## 2. 機能要件

### FR-10AB-1: sticky 上書き

- 手動 `PUT` 時 `sticky=true`（default）で `sync_breaches` から保護
- Redis / DB / memory 各 backend で sticky 状態を保持

### FR-10AB-2: sticky 解除

- `DELETE /ops/prometheus/alertmanager/breach-states/sticky` — 自動同期に復帰
- 監査 `alert.breach_state_sticky_cleared`

### FR-10AB-3: Ops UI

- sticky バッジ表示
- 「自動同期」ボタンで sticky 解除

---

## 3. スコープ外

- breach 変更履歴テーブル
- breaching-only フィルタ / CSV export

---

## 4. 成功条件

1. sticky ON 時 `sync_breaches` が状態を上書きしない
2. sticky 解除 API + 監査が動作
3. Ops UI 反映
4. pytest 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 10AA](requirements-phase10aa.md)
