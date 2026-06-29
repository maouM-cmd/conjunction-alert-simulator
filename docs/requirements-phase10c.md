# CAS Phase 10C — 要件定義書

**版:** 10C  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase10c.md`）  
**親ロードマップ:** [商用コンステ運用](requirements-commercial-ops.md)

---

## 1. 概要

Phase 10 第三フェーズ。Ops 回避試算に Δv パラメータ指定・スイープ探索・対策計画遷移連携を追加する。

| 変更箇所 | 内容 |
|---------|------|
| API | mitigation-sweep / mitigation-plan |
| UI | direction/Δv 入力、スイープ、試算→対策計画 |
| Service | best 選定、preview 付き triage |

---

## 2. 機能要件

### FR-10C-1: Ops UI パラメータ

- direction + Δv を指定して単発 preview

### FR-10C-2: Δv スイープ

- `POST .../mitigation-sweep` — 範囲走査、全試算を DB 保存

### FR-10C-3: best 選定

- `after_miss > before_miss` を満たす最小 Δv（なければ最大 after_miss）

### FR-10C-4: 対策計画連携

- `POST .../mitigation-plan` — preview をコメントに含め `mitigation_planned` へ

### FR-10C-5: 監査

- `alert.mitigation_sweep` / `alert.mitigation_plan`

### FR-10C-6: Ops UI ボタン

- Δv スイープ、試算→対策計画

---

## 3. スコープ外

- 燃料最適ソルバ、COLA 自動実行、DB スキーマ変更

**スイープデフォルト:** prograde, 0.01–0.10 m/s, step 0.01, max_trials 20

---

## 4. 成功条件

1. スイープ → best 返却 → 対策計画遷移
2. pytest 全件 PASS

---

## 5. 関連ドキュメント

- [Phase 10A](requirements-phase10a.md)
- [Phase 10B](requirements-phase10b.md)
