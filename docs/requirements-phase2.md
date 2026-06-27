# CAS Phase 2 — 要件定義書

**版:** 2.0  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements-phase2.md`）

---

## 1. 概要

Phase 2 では Phase 1 に **衝突確率 Pc** と **Space-Track オプション連携** を追加する。

---

## 2. 機能要件

### FR-P2-1: Pc 計算（Foster 2D）

- TCA 時点の miss distance b、位置不確かさ σ、合成ハードボディ半径 R から Pc を計算
- 式: `Pc = (R² / (2σ²)) × exp(-b² / (2σ²))`
- σ 未指定時は TLE エポック経過日数から推定（0.1〜2.0 km）
- 合成 R デフォルト: 15 m（衛星 10 m + デブリ 5 m）

### FR-P2-2: リスクレベル Pc 連動

| レベル | Pc |
|--------|-----|
| high | >= 1e-4 |
| medium | 1e-6 <= Pc < 1e-4 |
| low | Pc < 1e-6 |

Pc 計算時は距離ベースより Pc を優先。

### FR-P2-3: API 拡張

- `ConjunctionOut.pc` フィールド
- `ConjunctionsRequest.sigma_km` 任意上書き
- `ConjunctionsResponse.tle_provider`

### FR-P2-4: Space-Track 連携（オプション）

- `.env` に `SPACE_TRACK_USER`, `SPACE_TRACK_PASSWORD`, `TLE_PROVIDER`
- 未設定時は CelesTrak 継続
- Space-Track 失敗時は CelesTrak フォールバック

### FR-P2-5: UI

- 接近一覧に Pc 表示（科学記数法）
- σ 上書き入力（任意）

---

## 3. 非機能要件

| ID | 要件 |
|----|------|
| NFR-P2-1 | `.env` 未設定でも Phase 1 同等に動作 |
| NFR-P2-2 | pytest で Pc 計算ユニットテスト |
| NFR-P2-3 | 認証情報は `.env` のみ（リポに含めない） |

---

## 4. 成功条件

1. `/api/v1/conjunctions` に `pc` が含まれる
2. UI に Pc が表示される
3. CelesTrak フォールバック動作
4. `pytest tests/` 成功
5. Space-Track 設定時 `health.tle_provider` が `spacetrack` になる

---

## 5. スコープ外

- CDM インポート
- Monte Carlo Pc
- 複数衛星監視
- クラウドデプロイ
