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

- デブリ全件ループは Python 単スレッド。Phase 1.5 で並列化を検討
- 軌道 API は `step_minutes=5` で点列数を削減
- **高度プレフィルタ（Phase 1 実装済み）:** 衛星の平均高度 ±200 km 帯のデブリのみフル伝播。数千件カタログを 60 秒以内に収めるため `backend/app/services/analysis.py` で適用（カタログ 500 件超のとき有効）

## 外部依存

- CelesTrak: 無認証 GET。`GROUP=debris` は廃止のため、主要デブリ群（Iridium 33 / COSMOS 2251 等）をマージ取得。24h キャッシュ
