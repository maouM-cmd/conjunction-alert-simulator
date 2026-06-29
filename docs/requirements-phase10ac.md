# CAS Phase 10AC — 要件定義書

**版:** 10AC  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10ac.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第二十九フェーズ。10AB でスコープ外とした breaching-only フィルタと breach 変更履歴を実装する。

| 変更箇所 | 内容 |
|---------|------|
| DB | `fleet_alert_breach_history` |
| Service | `breach_history_service` — 遷移記録・一覧 |
| API | `breaching_only` クエリ、history JSON/CSV |
| UI | breaching チェックボックス、履歴テーブル、CSV ダウンロード |
| env | `ALERTMANAGER_BREACH_HISTORY_ENABLED` |

---

## 2. 機能要件

### FR-10AC-1: breaching-only フィルタ

- `GET breach-states?breaching_only=true` — `is_breaching=true` のみ返却
- 単艦隊・管理者横断の両方で `total` はフィルタ後件数

### FR-10AC-2: breach 変更履歴

- `sync_breaches` / 手動 `PUT` / sticky 解除で履歴行を記録（opt-in）
- `source`: `sync` / `manual` / `sticky_clear`

### FR-10AC-3: history API

- `GET breach-states/history` — JSON（default）または `format=csv`
- 履歴無効時は 503

### FR-10AC-4: Ops UI

- breaching のみチェックボックス（艦隊 + 管理者横断）
- 履歴テーブル + CSV ダウンロード
- 履歴無効時は案内表示

---

## 3. スコープ外

- 管理者横断 breach 履歴（fleet_id 省略）
- 履歴 retention / purge Celery タスク
- breaching-only の Prometheus / Alertmanager 連携

---

## 4. 成功条件

1. breaching-only フィルタが単艦隊・横断で動作
2. 履歴記録 + JSON/CSV API が動作
3. Ops UI 反映
4. pytest 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 10AB](requirements-phase10ab.md)
