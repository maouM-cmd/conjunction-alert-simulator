# CAS Phase 10AE — 要件定義書

**版:** 10AE  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10ae.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第三十一フェーズ。10AD でスコープ外とした breaching-only Prometheus 連携と breach 履歴フィルタを実装する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `render_fleet_alert_rules(breaching_only)` — breach gauge expr |
| Service | `list_history` / `list_all_history` — source / breaching_only フィルタ |
| API | `GET fleet-alert-rules?breaching_only=true`、`GET history` フィルタ拡張 |
| UI | 履歴 source セレクト + breaching のみチェックボックス |

---

## 2. 機能要件

### FR-10AE-1: breach gauge ルール雛形

- `GET fleet-alert-rules?breaching_only=true` — expr を breach Gauge ベースに切替
- alert 名は Alertmanager push と一致維持

### FR-10AE-2: 履歴フィルタ

- `GET history` に `source`（sync / manual / sticky_clear）と `breaching_only`
- 単艦隊・管理者横断の両方で `total` はフィルタ後

### FR-10AE-3: Ops UI

- 履歴セクション（単艦隊 + 管理者）にフィルタ UI
- CSV ダウンロードにもフィルタ反映

---

## 3. スコープ外

- per-fleet breach 履歴 retention
- fleet-alert-rules Ops UI
- breach_state_store ベースの breaching 艦隊のみ rule 出力

---

## 4. 成功条件

1. breach gauge expr ルールが生成される
2. 履歴 source / breaching_only フィルタが動作
3. Ops UI 反映
4. pytest 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 10AD](requirements-phase10ad.md)
