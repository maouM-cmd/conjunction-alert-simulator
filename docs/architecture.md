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
- 単一衛星 API: デフォルト Foster、`use_advanced_pc=true` で Alfriend（`pc_conjunction.py`, `analysis.py`）

### Phase 4A-Ext: 一覧 API Advanced Pc

```
detect_conjunctions → Foster Pc (default)
                   → use_advanced_pc?
                        ├─ false → pc=foster, pc_method_used=foster
                        └─ true  → pc=Alfriend, MC on top-5 only
```

- `pc_conjunction.py`: TLE ペア + TCA index → encounter plane Pc（等方 σ、grid 80×120）
- `conjunction_out.py`: `ConjunctionEvent` → `ConjunctionOut`
- batch: 同一 `use_advanced_pc` を worker に伝播（`batch_analysis.py`）

## Phase 4B: Space-Track CDM 運用連携

- `spacetrack_client.py` — 共通認証 + JSON GET
- `spacetrack_cdm_fetcher.py` — `cdm_public` 一覧（24h キャッシュ）
- `cdm_alert_compare.py` — カタログ TLE 解決 + Foster 比較
- `cdm_export.py` — 接近イベント → CDM KVN
- UI「CDM アラート」タブ

## Phase 4C: Docker デプロイ

```
docker compose up
    → uvicorn :8000 (1 worker)
    → volume cas-cache → data/cache/
    → /app/ frontend + /api/v1/*
```

- [`Dockerfile`](../Dockerfile) + [`docker-compose.yml`](../docker-compose.yml)
- 本番: reload なし、`0.0.0.0:8000`
- 手順: [`docs/deploy.md`](deploy.md)

## Phase 2: TLE プロバイダ

- デフォルト: CelesTrak（24h キャッシュ）
- オプション: Space-Track（`.env` 認証、`TLE_PROVIDER=spacetrack`）
- 失敗時: CelesTrak フォールバック（`tle_provider: celestrak (fallback)`）

## 外部依存

- CelesTrak: 無認証 GET。主要デブリ群をマージ取得
- Space-Track: 要アカウント。利用規約に従う
