# アーキテクチャ

## 構成

```
Frontend (CesiumJS)  ←→  FastAPI  ←→  Services
                              ├── tle_fetcher   (CelesTrak + cache)
                              ├── propagator    (SGP4 + TEME positions)
                              └── conjunction   (miss distance, risk)
```

## 技術選定

| レイヤ | 選定 | 理由 |
|--------|------|------|
| 軌道伝播 | `sgp4` + `numpy` | TLE 標準。Skyfield は時刻ユーティリティに限定 |
| API | FastAPI + Pydantic | OpenAPI 自動生成 |
| 3D | CesiumJS | 地球・タイムライン組込み |
| キャッシュ | JSON ファイル + mtime TTL | DB 不要 |

## 座標系

- SGP4 出力: TEME（True Equator Mean Equinox）
- 距離計算: TEME 直交座標（km）のユークリッド距離
- Cesium 表示: TEME → ICRF 近似として `Cesium.ReferenceFrame.INERTIAL` に描画（Phase 1）

## 性能

- デブリ全件ループは Python 単スレッド
- 軌道 API は `step_minutes=5` で点列数を削減
- **高度プレフィルタ:** 衛星平均高度 ±200 km（`analysis.py`、500 件超カタログ時）
- **Pc 計算:** Foster 2D（`pc_calculator.py`）、イベントは Pc 降順ソート

## Phase 4A: Encounter Plane Pc

- CDM RTN 共分散 → TEME → encounter plane 2×2（`encounter_plane.py`, `cdm_covariance.py`）
- CDM 比較: Foster / Alfriend / Monte Carlo 並列（`pc_advanced.py`）
- 単一衛星 API は Foster 維持、CDM compare のみ advanced Pc

## Phase 2: TLE プロバイダ

- デフォルト: CelesTrak（24h キャッシュ）
- オプション: Space-Track（`.env` 認証、`TLE_PROVIDER=spacetrack`）
- 失敗時: CelesTrak フォールバック（`tle_provider: celestrak (fallback)`）

## 外部依存

- CelesTrak: 無認証 GET。主要デブリ群をマージ取得
- Space-Track: 要アカウント。利用規約に従う
