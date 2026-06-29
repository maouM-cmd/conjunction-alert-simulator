# CAS Phase 10W — 要件定義書

**版:** 10W  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10w.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第二十三フェーズ。10V で先送りした silence 一括削除 API と Ops UI silence 管理を実装する。

| 変更箇所 | 内容 |
|---------|------|
| Service | `delete_silences_for_fleet` |
| API | `DELETE /ops/prometheus/alertmanager/silences?fleet_id=` |
| UI | Ops パネル silence 一覧・作成・削除 |

---

## 2. 機能要件

### FR-10W-1: silence 一括削除

- fleet 単位（+ optional `alertname`）で active silence を削除
- 0 件はエラーではない

### FR-10W-2: Ops UI silence 管理

- 一覧・作成・単体削除・艦隊一括削除
- silences 無効時は非エラー表示

---

## 3. スコープ外

- breach DB 永続化、metrics + Celery 同時 push、複数 ID チェックボックス bulk

---

## 4. 成功条件

1. fleet 一括削除 API が動作
2. Ops UI から silence 管理可能
3. pytest 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 10V](requirements-phase10v.md)
- [Phase 10T](requirements-phase10t.md)
