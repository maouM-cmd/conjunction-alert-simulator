# Conjunction Alert Simulator — 要件定義書

**版:** 1.0  
**日付:** 2026-06-28  
**正本:** 本ファイル（`docs/requirements.md`）

---

## 1. プロダクト概要

| 項目 | 内容 |
|------|------|
| 名称 | Conjunction Alert Simulator（CAS） |
| 概要 | 衛星 TLE から7日間のデブリ接近を検出し、3D 可視化と回避試算を行う Web アプリ |
| 目的 | SpaceX Starlink 型の衝突回避運用の縮小版を OSS として構築し、ポートフォリオ・学習・採用アピールに使う |

---

## 2. ステークホルダーと利用者

| 利用者 | 目的 | Phase 1 で満たすこと |
|--------|------|---------------------|
| 開発者本人 | ポートフォリオ・軌道力学学習 | デモ可能な完成品 |
| 小型衛星・大学衛星チーム | 接近アラートの参考 | TLE 入力で結果が出る |
| OSS 閲覧者 | GitHub デモ・技術ブログ | README + デモ資料 |

**非ターゲット:** 本番 SLA、Space-Track 有料連携、ADR ハードウェアシミュ。

---

## 3. 機能要件（FR）

### FR-1: 衛星 TLE 入力

- 自衛星 TLE（2行または3行）をテキスト入力できる
- 形式バリデーション（行数・チェックサム・軌道要素範囲）
- サンプル TLE（ISS）をワンクリック読み込み

### FR-2: デブリカタログ取得

- CelesTrak からデブリ TLE カタログを取得（`gp.php?GROUP=debris&FORMAT=tle`）
- ローカルキャッシュ TTL 24時間。取得失敗時はキャッシュで継続（degraded）
- Phase 1 は全デブリ対象。性能問題時は高度フィルタを Phase 1.5 で追加

### FR-3: 軌道伝播

- SGP4（`sgp4`）で衛星・各デブリを伝播
- 期間: 現在 UTC から7日間
- 刻み: **1分** — 5 km 閾値の接近検出に十分な精度と、数千デブリ×7日を60秒以内に収める性能のバランス

### FR-4: 接近イベント検出

- 衛星と各デブリの最接近距離（Miss Distance）を計算
- 閾値 **5 km 以内** を接近イベントとして抽出
- イベント属性: NORAD ID、名称、TCA（UTC）、miss distance（km）、相対速度（km/s）、リスクレベル

**リスクレベル（距離ベース）:**

| レベル | 条件 |
|--------|------|
| high | miss distance < 1 km |
| medium | 1 km ≤ miss distance < 3 km |
| low | 3 km ≤ miss distance < 5 km |

### FR-5: REST API

- `GET /health` — 死活監視
- `POST /api/v1/conjunctions` — 接近イベント一覧
- `POST /api/v1/orbit` — 軌道点列（3D 用）
- `POST /api/v1/maneuver/preview` — 回避後 miss distance 試算

### FR-6: 3D 可視化（CesiumJS）

- 地球 + 衛星軌道（青）+ 選択デブリ軌道（赤）
- イベント一覧クリック → デブリ軌道ハイライト
- TCA マーカー、7日間タイムスライダー
- Phase 1: 単一衛星 vs 選択デブリ1件の詳細表示

### FR-7: 回避マニューバ試算

- prograde / retrograde / normal、Δv 0.01〜1.0 m/s
- 回避後 miss distance の Before/After 表示
- 燃料最適化なし（固定 Δv の効果確認のみ）

---

## 4. 非機能要件（NFR）

| ID | 要件 | 目標値 |
|----|------|--------|
| NFR-1 | 初回接近解析（全デブリ・7日・1分刻み） | 60秒以内（ローカル PC） |
| NFR-2 | API タイムアウト | 90秒 |
| NFR-3 | ブラウザ | Chrome / Edge 最新 |
| NFR-4 | バックエンド | Python 3.12 + FastAPI |
| NFR-5 | フロント | 静的 HTML + CesiumJS |
| NFR-6 | エラーメッセージ | 日本語 |
| NFR-7 | ライセンス | MIT |
| NFR-8 | CelesTrak 障害 | キャッシュ TLE で degraded 動作 |

---

## 5. スコープ外（Phase 1）

- Space-Track 認証連携
- 高精度 Pc（Foster 公式等）
- 複数衛星同時監視
- ADR 物理シミュ
- ユーザー認証・課金
- クラウド本番デプロイ

---

## 6. 成功条件

1. 自衛星 TLE 入力 → 7日以内 5 km 接近デブリ一覧が **60秒以内** に表示
2. 一覧から1件選択 → Cesium で衛星・デブリ軌道と TCA が 3D 表示
3. Δv 指定 → 回避後 miss distance が Before/After 表示
4. README + デモ GIF 付きで **GitHub 公開済み**（https://github.com/maouM-cmd/conjunction-alert-simulator）
5. 本要件定義書と実装が一致

---

## 7. マイルストーン（12週間）

| 週 | 成果物 |
|----|--------|
| W1-2 | 軌道伝播 CLI |
| W3-4 | 接近検出 + TLE 取得 |
| W5-6 | FastAPI |
| W7-9 | CesiumJS 3D |
| W10-11 | 回避試算 UI |
| W12 | デモ・公開 |

---

## 8. 商用コンステ運用版

大規模コンステ（1,000+ 衛星）向け運用ワークフロー拡張の要件は **[requirements-commercial-ops.md](requirements-commercial-ops.md)** を参照。Phase 9A: [requirements-phase9a.md](requirements-phase9a.md)、Phase 9B: [requirements-phase9b.md](requirements-phase9b.md)。
