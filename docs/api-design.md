# API 設計書

**版:** 1.0  
**ベース URL:** `http://127.0.0.1:8000`

---

## 共通

- Content-Type: `application/json`
- 時刻: ISO 8601 UTC（末尾 `Z`）
- エラーレスポンス: `{ "detail": "日本語メッセージ" }` または FastAPI バリデーション形式

---

## GET /health

**レスポンス 200:**

```json
{
  "status": "ok",
  "tle_cache_age_hours": 2.5,
  "tle_cache_stale": false
}
```

---

## POST /api/v1/conjunctions

接近イベントを検出する。

### リクエスト

```json
{
  "tle": "ISS (ZARYA)\n1 25544U 98067A   25179.51782528  .00016717  00000+0  10270-3 0  9993\n2 25544  51.6347  74.8662 0004176 315.5599 138.2340 15.50909589423071",
  "duration_days": 7,
  "threshold_km": 5.0,
  "step_minutes": 1
}
```

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| tle | string | yes | — | 3行または2行 TLE |
| duration_days | float | no | 7 | 解析期間（日） |
| threshold_km | float | no | 5.0 | 接近閾値（km） |
| step_minutes | int | no | 1 | 伝播刻み（分） |

### レスポンス 200

```json
{
  "satellite": {
    "name": "ISS (ZARYA)",
    "norad_id": 25544
  },
  "analysis_window": {
    "start": "2026-06-28T00:00:00Z",
    "end": "2026-07-05T00:00:00Z"
  },
  "threshold_km": 5.0,
  "conjunctions": [
    {
      "debris_norad_id": 12345,
      "debris_name": "DEBRIS EXAMPLE",
      "debris_tle": "DEBRIS EXAMPLE\n1 12345U ...\n2 12345 ...",
      "tca": "2026-06-30T12:34:56Z",
      "miss_distance_km": 2.3,
      "relative_velocity_kms": 7.1,
      "risk_level": "medium"
    }
  ],
  "debris_catalog_count": 4200,
  "computation_time_ms": 8420,
  "tle_cache_stale": false
}
```

`conjunctions` は `miss_distance_km` 昇順でソート。

### エラー

| コード | 条件 |
|--------|------|
| 400 | TLE 形式不正 |
| 504 | 計算タイムアウト（90秒超） |

---

## POST /api/v1/orbit

軌道点列を返す（3D 描画用）。

### リクエスト

```json
{
  "tle": "...",
  "duration_days": 7,
  "step_minutes": 5
}
```

3D 描画用は性能のため `step_minutes` デフォルト **5**。

### レスポンス 200

```json
{
  "name": "ISS (ZARYA)",
  "norad_id": 25544,
  "points": [
    {
      "time": "2026-06-28T00:00:00Z",
      "position_km": { "x": 1234.5, "y": -5678.9, "z": 9012.3 }
    }
  ]
}
```

座標系: **TEME**（km）。Cesium 側で ECEF/固定座標系に変換。

---

## POST /api/v1/maneuver/preview

指定 Δv 適用後の最接近距離を試算。

### リクエスト

```json
{
  "satellite_tle": "...",
  "debris_tle": "...",
  "direction": "prograde",
  "delta_v_ms": 0.1,
  "duration_days": 7,
  "step_minutes": 1
}
```

| direction | 説明 |
|-----------|------|
| prograde | 速度方向（+V） |
| retrograde | 速度反対（-V） |
| normal | 角運動量方向（R × V） |

### レスポンス 200

```json
{
  "before": {
    "tca": "2026-06-30T12:34:56Z",
    "miss_distance_km": 2.3,
    "relative_velocity_kms": 7.1
  },
  "after": {
    "tca": "2026-06-30T12:35:10Z",
    "miss_distance_km": 4.8,
    "relative_velocity_kms": 7.0
  },
  "delta_v_applied_ms": 0.1,
  "direction": "prograde"
}
```

---

## Pydantic モデル対応表

| モデル | ファイル |
|--------|---------|
| ConjunctionsRequest | `backend/app/models/schemas.py` |
| ConjunctionsResponse | 同上 |
| OrbitRequest / OrbitResponse | 同上 |
| ManeuverPreviewRequest / ManeuverPreviewResponse | 同上 |

---

## OpenAPI

起動後 `http://127.0.0.1:8000/docs` で Swagger UI を参照。
