# CAS Phase 10Y — 要件定義書

**版:** 10Y  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10y.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第二十五フェーズ。10W/10X で先送りした silence 複数 ID 選択式 bulk 削除を実装する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `delete_silences_by_ids` |
| API | `POST /ops/prometheus/alertmanager/silences/bulk-delete` |
| UI | チェックボックス選択削除 |

---

## 2. 機能要件

### FR-10Y-1: 選択 ID bulk 削除

- `silence_ids` リストで指定分を削除
- fleet スコープ認可（10V 単体削除と同様）
- 部分失敗許容

### FR-10Y-2: Ops UI チェックボックス

- 行選択 + 全選択 + 「選択した silence を削除」

---

## 3. スコープ外

- DB 共有 dual push 拡張、breach 状態 UI

---

## 4. 成功条件

1. 選択 ID bulk 削除 API が動作
2. Ops UI からチェックボックス削除可能
3. pytest 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 10W](requirements-phase10w.md)
- [Phase 10X](requirements-phase10x.md)
