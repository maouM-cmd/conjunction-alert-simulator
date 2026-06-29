# API 設計書

**版:** 4A  
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
  "checks": {
    "postgres": "ok",
    "redis": "ok",
    "worker": "ok"
  },
  "tle_cache_age_hours": 2.5,
  "tle_cache_stale": false,
  "tle_provider": "celestrak",
  "spacetrack_configured": false,
  "spacetrack_cdm_available": false,
  "alert_delivery_configured": false,
  "alert_delivery_format": null
}
```

`alert_delivery_configured`: 通知配信に必要な env が揃っている場合 `true`。  
`alert_delivery_format`: `generic` | `slack` | `slack_bot` | `smtp` | `pagerduty`（未設定時 `null`）。秘密値は返さない。

**Phase 9E:** `status` は `ok` | `degraded`（設定済み check が全て ok なら ok）。`checks.*` は `ok` | `error` | `skipped`。HTTP は常に **200**（Render liveness 互換）。

---

## GET /metrics（Phase 9D / 10B）

Prometheus テキスト形式（`text/plain; version=0.0.4`）。

**レスポンス 200 例（抜粋）:**

```
cas_open_alerts_total 3.0
cas_screening_runs_total{status="completed"} 12.0
cas_celery_queue_depth 0.0
cas_screening_lag_seconds{fleet_id="..."} 7200.0
cas_screening_overdue_fleets 0.0
cas_http_requests_total{method="GET",status_class="2xx"} 42.0
cas_api_availability_ratio 0.9995
cas_api_slo_ok 1.0
cas_info{version="1.19.0"} 1.0
```

| メトリクス | 説明 |
|-----------|------|
| `cas_open_alerts_total` | status=open のアラート件数（DB） |
| `cas_screening_runs_total{status}` | screening run 件数（DB、status ラベル） |
| `cas_celery_queue_depth` | Celery デフォルトキュー深度（Redis LLEN、未設定時 omit） |
| `cas_screening_lag_seconds{fleet_id}` | 最終 completed 親 run からの経過秒（Phase 10B） |
| `cas_screening_overdue_fleets` | lag &gt; `SLA_SCREENING_MAX_LAG_HOURS` の艦隊数 |
| `cas_http_requests_total{method,status_class}` | HTTP リクエスト Counter（`/metrics` 除外） |
| `cas_api_availability_ratio` | ローリング窓 API 可用性（1 - 5xx/total）（Phase 10H） |
| `cas_api_slo_ok` | 1 = SLO 達成、0 = breach（Phase 10H） |
| `cas_info{version}` | アプリバージョン |

**SLA 監視クエリ例（Phase 10B / 10H）:**

```promql
# API 可用性（アプリ内ローリング窓 — scrape 時点）
cas_api_availability_ratio

# API SLO breach アラート
cas_api_slo_ok == 0

# API 可用性（Prometheus rate ベース — 月次 99.9% 目標）
1 - (
  sum(rate(cas_http_requests_total{status_class="5xx"}[30d]))
  / sum(rate(cas_http_requests_total[30d]))
) >= 0.999

# スクリーニング overdue 艦隊
cas_screening_overdue_fleets > 0
```

`DATABASE_URL` 未設定時は DB 由来メトリクスを省略。認証なし（9E で API Key 検討）。

---

## POST /api/v1/conjunctions

接近イベントを検出する。

### リクエスト

```json
{
  "tle": "ISS (ZARYA)\n1 25544U 98067A   25179.51782528  .00016717  00000+0  10270-3 0  9993\n2 25544  51.6347  74.8662 0004176 315.5599 138.2340 15.50909589423071",
  "duration_days": 7,
  "threshold_km": 5.0,
  "step_minutes": 1,
  "sigma_km": 1.0
}
```

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| tle | string | yes | — | 3行または2行 TLE |
| duration_days | float | no | 7 | 解析期間（日） |
| threshold_km | float | no | 5.0 | 接近閾値（km） |
| step_minutes | int | no | 1 | 伝播刻み（分） |
| sigma_km | float | no | null | 位置不確かさ σ (km)。未指定時 TLE 経過日数から推定 |
| use_advanced_pc | bool | no | false | true 時 encounter plane Alfriend Pc（opt-in） |
| use_anisotropic_cov | bool | no | false | TLE RTN 非等方共分散（`use_advanced_pc=true` 時のみ） |
| notify_webhook | bool | no | false | high/medium イベントを `ALERT_WEBHOOK_URL` に POST |
| cdm_text | string | no | null | 共分散付き CDM KVN（任意） |
| apply_cdm_covariance | bool | no | false | `cdm_text` 指定時、該当デブリの Pc に CDM encounter 共分散を適用 |
| use_altitude_prefilter | bool | no | true | 高度帯±200 km プリフィルタ（カタログ 500 件超時） |
| auto_spacetrack_cdm | bool | no | false | Space-Track `cdm_public` 自動マージ（`use_advanced_pc=true` 必須） |
| spacetrack_cdm_pc_min | float | no | null | auto 取得時の Pc 下限 |

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
      "risk_level": "medium",
      "pc": 1.23e-05,
      "pc_foster": 1.1e-05,
      "pc_alfriend": 1.23e-05,
      "pc_monte_carlo": 1.22e-05,
      "pc_method_used": "encounter_advanced",
      "covariance_source": "isotropic",
      "sigma_source": "tle_age"
    }
  ],
  "debris_catalog_count": 4200,
  "debris_candidates_count": 1180,
  "altitude_prefilter_applied": true,
  "computation_time_ms": 8420,
  "tle_cache_stale": false,
  "tle_provider": "celestrak",
  "webhook": null,
  "spacetrack_cdm_records_fetched": 0,
  "spacetrack_cdm_events_merged": 0,
  "spacetrack_cdm_degraded": false
}
```

`conjunctions` は Phase 2 以降 **Pc 降順** でソート。

`use_advanced_pc=false` 時は `pc` のみ（Foster）、`pc_method_used: foster`。  
`use_advanced_pc=true` 時は primary `pc` = Alfriend、MC は Alfriend 降順上位 5 件のみ `pc_monte_carlo` が非 null。  
`use_anisotropic_cov=true`（advanced 時のみ）で `covariance_source: tle_rtn_anisotropic`。  
`COV_PROPAGATION_ENABLED=true` 時は `covariance_source: tle_rtn_propagated`（Phase 10K）。  
`apply_cdm_covariance=true` + `cdm_text` で該当デブリに `sigma_source: cdm_covariance` / `covariance_source: cdm_encounter`。  
`CDM_TCA_SHIFT_ENABLED=true` 時は `covariance_source: cdm_encounter_tca_shift`（Phase 10M）。
`auto_spacetrack_cdm=true` で Space-Track から CDM を自動マージ（`cdm_text` がある場合は手動優先）。認証未設定時は merged=0 で解析継続。  
`notify_webhook=true` で解析後に high/medium かつ Pc ≥ `ALERT_PC_THRESHOLD` を通知 POST。レスポンス `webhook` に結果（sent / alert_count / message）。  
`ALERT_WEBHOOK_FORMAT=slack` で Slack Incoming Webhook 形式 `{"text":"..."}`。  
`ALERT_WEBHOOK_FORMAT=slack_bot` で Slack Web API `chat.postMessage`（`SLACK_BOT_TOKEN` + `SLACK_CHANNEL_ID`）。  
`ALERT_WEBHOOK_FORMAT=smtp` で SMTP メール（`SMTP_HOST` + `SMTP_FROM` + `SMTP_TO`、任意 `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_USE_TLS`）。  
`ALERT_WEBHOOK_FORMAT=pagerduty` で PagerDuty Events API v2（`PAGERDUTY_ROUTING_KEY`、`ALERT_WEBHOOK_URL` 不要）（Phase 10L）。  
`PAGERDUTY_LIFECYCLE_ENABLED=true` 時は `dedup_key=cas-alert-{alert_id}` で trigger / acknowledge / resolve を連動（Phase 10O）。新規 screening アラートは per-alert trigger、Ops `acknowledged` / `closed` / `false_positive` で lifecycle イベント送信。
一覧 API の `pc_method_used`: `foster` | `encounter_advanced`（CDM compare の `foster_only` とは別）。

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

---

## POST /api/v1/cdm/parse

CDM テキストを構造化 JSON に変換する。

### リクエスト

```json
{
  "cdm_text": "CCSDS_CDM_VERS = 1.0\nTCA = 2026/180/15:57:36.000\n..."
}
```

### レスポンス 200

```json
{
  "tca": "2026-06-29T15:57:36Z",
  "miss_distance_km": 29.75,
  "relative_speed_kms": 7.283,
  "pc_external": 3.2e-05,
  "sat1_designator": "1998-067A",
  "sat2_designator": "1993-036ATM",
  "sat1_object": "ISS (ZARYA)",
  "sat2_object": "COSMOS 2251 DEB"
}
```

---

## POST /api/v1/cdm/compare

CDM 外部値と CAS SGP4 計算値を比較する。

### リクエスト

```json
{
  "cdm_text": "...",
  "satellite_tle": "...",
  "debris_tle": "...",
  "duration_days": 7,
  "step_minutes": 1,
  "sigma_km": null
}
```

### レスポンス 200

```json
{
  "cdm": {
    "miss_distance_km": 29.75,
    "pc": 3.2e-05,
    "relative_velocity_kms": 7.283,
    "tca": "2026-06-29T15:57:36Z"
  },
  "cas": {
    "miss_distance_km": 30.12,
    "pc": 2.8e-05,
    "relative_velocity_kms": 7.29,
    "tca": "2026-06-29T15:58:00Z"
  },
  "delta_miss_km": 0.37,
  "delta_pc_ratio": 0.875,
  "cas_sigma_km": 0.1523,
  "sigma_source": "cdm_covariance",
  "pc_methods": {
    "foster": 2.5e-05,
    "alfriend": 2.8e-05,
    "monte_carlo": 2.79e-05
  },
  "pc_method_used": "encounter_advanced",
  "encounter_miss_km": 29.5
}
```

`sigma_source`: `manual` | `cdm_covariance` | `tle_age`  
`pc_method_used`: `foster_only` | `encounter_advanced`  
`cas.pc` は primary Pc（encounter 時 Alfriend、それ以外 Foster）

---

## POST /api/v1/cdm/fetch

Space-Track `cdm_public` から CDM アラート一覧を取得する（要 `.env` 認証）。

### リクエスト

```json
{
  "norad_id": 25544,
  "pc_min": 1e-5,
  "days_ahead": 7,
  "limit": 25
}
```

### レスポンス 200

```json
{
  "records": [
    {
      "cdm_id": "123456",
      "tca": "2026-06-30T12:00:00Z",
      "pc": 1.2e-05,
      "min_range_km": 2.5,
      "sat1_id": 25544,
      "sat2_id": 99999,
      "sat1_name": "ISS (ZARYA)",
      "sat2_name": "DEB",
      "emergency_reportable": false,
      "has_rtn_covariance": true
    }
  ],
  "source": "spacetrack",
  "cached": false,
  "degraded": false
}
```

認証未設定時 **503**。

`has_rtn_covariance`: 一覧または detail 取得済みレコードに RTN 共分散（`SAT1_CR_R` 等）がある場合 `true`。RTN 無しの一覧行は `false`（compare-alert 時に lazy detail 取得を試行）。

---

## POST /api/v1/cdm/compare-alert

Space-Track CDM レコードと CAS を比較。相手 NORAD の TLE はデブリカタログから自動解決。

### リクエスト

```json
{
  "satellite_tle": "...",
  "record": { "cdm_id": "123", "sat1_id": 25544, "sat2_id": 99999, "...": "..." },
  "duration_days": 7,
  "step_minutes": 1
}
```

### レスポンス 200

`compare` に `CdmCompareResponse`、加えて `debris_tle` / `debris_norad_id`。TLE 未発見時 **404**。

---

## POST /api/v1/cdm/export

CAS 接近イベントから CDM KVN テキストを生成。

### リクエスト

```json
{
  "satellite_tle": "...",
  "debris_tle": "...",
  "tca": "2026-06-30T12:00:00Z",
  "miss_distance_km": 2.5,
  "relative_velocity_kms": 7.1,
  "pc": 1.2e-05,
  "sigma_km": null
}
```

### レスポンス 200

```json
{ "cdm_text": "CCSDS_CDM_VERS = 1.0\n..." }
```

---

## POST /api/v1/conjunctions/batch

複数衛星 TLE を一括解析する（デブリカタログは 1 回取得）。

### リクエスト

```json
{
  "satellites": [
    { "name": "SAT-1", "tle": "..." },
    { "name": "SAT-2", "tle": "..." }
  ],
  "threshold_km": 50,
  "duration_days": 7,
  "step_minutes": 1,
  "sigma_km": null,
  "use_advanced_pc": false
}
```

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| satellites | array | yes | — | `{ name, tle }` 最大 25 件 |
| threshold_km | float | no | 50 | 接近閾値（km） |
| duration_days | float | no | 7 | 解析期間（日） |
| step_minutes | int | no | 1 | 伝播刻み（分） |
| sigma_km | float | no | null | 位置不確かさ σ (km) |
| use_advanced_pc | bool | no | false | encounter plane Alfriend Pc（opt-in） |
| use_anisotropic_cov | bool | no | false | TLE RTN 非等方共分散（`use_advanced_pc=true` 時のみ） |
| use_altitude_prefilter | bool | no | true | 高度帯±200 km プリフィルタ（カタログ 500 件超時） |
| auto_spacetrack_cdm | bool | no | false | 各衛星に Space-Track CDM 自動マージ（`use_advanced_pc=true` 必須） |
| spacetrack_cdm_pc_min | float | no | null | auto 取得時の Pc 下限 |

`summary` に `spacetrack_cdm_events_merged`（fleet 合計）と `spacetrack_cdm_satellites_with_merge` を含む。各 `results[]` 要素は単一衛星 `/conjunctions` レスポンスと同型（CDM メタ含む）。

---

## POST /api/v1/alerts/webhook/test

設定済みの通知配信先へテスト ping を POST する（Incoming Webhook / Slack Bot 共通）。

### レスポンス

| コード | 条件 |
|--------|------|
| 200 | POST 成功 |
| 503 | 配信先未設定（`ALERT_WEBHOOK_URL` または `SLACK_BOT_TOKEN`+`SLACK_CHANNEL_ID` または `SMTP_HOST`+`SMTP_FROM`+`SMTP_TO`） |

```json
{
  "sent": true,
  "alert_count": 0,
  "degraded": false,
  "message": "Webhook POST 成功 (200)。"
}
```

最大 25 衛星。ProcessPool 並列実行（2 衛星以上）。

### レスポンス 200

```json
{
  "results": [ /* ConjunctionsResponse の配列 */ ],
  "summary": {
    "satellite_count": 2,
    "total_events": 15,
    "highest_pc": 1.2e-05,
    "highest_pc_satellite": "SAT-1",
    "highest_pc_debris": "COSMOS 2251 DEB"
  },
  "computation_time_ms": 120000,
  "tle_provider": "celestrak",
  "parallel": true,
  "worker_count": 4
}
```

タイムアウト: 600 秒。

---

## Fleet Registry（Phase 9A）

**前提:** 環境変数 `DATABASE_URL` が設定されていること。未設定時は全エンドポイント **503**。

### POST /api/v1/fleets

艦隊を作成する。

**リクエスト:**

```json
{
  "name": "Demo Constellation",
  "description": "LEO demo fleet",
  "tags": ["leo", "demo"]
}
```

**レスポンス 201:** `FleetOut`（`satellite_count: 0`）

### GET /api/v1/fleets

アクティブな艦隊一覧。各要素に `satellite_count` を含む。

### GET /api/v1/fleets/{fleet_id}

艦隊詳細。存在しない / 論理削除済みは **404**。

### PATCH /api/v1/fleets/{fleet_id}

`name` / `description` / `tags` の部分更新。

### DELETE /api/v1/fleets/{fleet_id}

論理削除（`active=false`）。**204**。

### POST /api/v1/fleets/{fleet_id}/satellites

衛星を艦隊に追加。TLE は既存 `parse_tle` で検証。

**リクエスト:**

```json
{
  "name": "ISS (ZARYA)",
  "norad_id": 25544,
  "tle": "ISS (ZARYA)\n1 25544U ...\n2 25544 ..."
}
```

`name` / `norad_id` 省略時は TLE から推定。同一艦隊内 NORAD 重複は **409**。

### GET /api/v1/fleets/{fleet_id}/satellites

クエリ: `limit`（default 100, max 500）、`offset`（default 0）。

**レスポンス 200:**

```json
{
  "items": [ /* SatelliteOut */ ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

### PATCH /api/v1/satellites/{satellite_id}

`name` または `tle` を更新。TLE 変更時は旧 TLE を `tle_revisions` に保存（最新 2 世代保持）。

### DELETE /api/v1/satellites/{satellite_id}

衛星を論理削除。**204**。

### POST /api/v1/satellites/{satellite_id}/rollback

直近 revision の TLE を現行に復元。revision なしは **404**。

---

## Scheduled Screening（Phase 9B）

**前提:** `DATABASE_URL` と `REDIS_URL` が設定されていること。未設定時は **503**。

### POST /api/v1/screening/schedules

スクリーニングスケジュールを作成。cron 式は 5 フィールド（`croniter` 検証）。

**リクエスト例:**

```json
{
  "fleet_id": "<uuid>",
  "name": "Daily LEO",
  "cron_expression": "0 0 * * *",
  "threshold_km": 5.0,
  "duration_days": 7,
  "notify_on_complete": false
}
```

### GET /api/v1/screening/schedules

アクティブなスケジュール一覧。`fleet_id` クエリで絞り込み可。

### PATCH /api/v1/screening/schedules/{schedule_id}

解析パラメータ / cron / notify_on_complete 等を部分更新。

### DELETE /api/v1/screening/schedules/{schedule_id}

論理削除。**204**。

### POST /api/v1/screening/schedules/{schedule_id}/run

手動即時 Run を enqueue。**202** — Celery eager 時は同期完了後の Run 状態を返す。

### GET /api/v1/screening/runs

Run 履歴。`fleet_id` / `status` フィルタ、`limit` / `offset` ページネーション。

**Run status:** `pending` | `running` | `completed` | `failed` | `dead_letter`

**Phase 9D:** 艦隊が `SCREENING_CHUNK_SIZE`（default 50）を超える場合、親 run が N 個の子 run（chunk）を enqueue。全 chunk 完了後に親 run を集計完了。子 run は `parent_run_id` / `chunk_index` を持つ。

---

## Ops Dashboard（Phase 9C）

**前提:** `DATABASE_URL` 設定済み。

### GET /api/v1/ops/fleets/{fleet_id}/summary

open / acknowledged / mitigation_planned / closed 件数と最新 screening run。

### GET /api/v1/ops/alerts

クエリ: `fleet_id`, `status`, `limit`, `offset`。

### PATCH /api/v1/ops/alerts/{alert_id}

```json
{ "status": "acknowledged", "comment": "確認済み" }
```

**遷移:** open → acknowledged | false_positive → mitigation_planned | closed | false_positive

**レスポンス拡張（Phase 10A）:** `ConjunctionAlertOut.latest_mitigation_preview` — 最新回避試算（なければ null）。

### POST /api/v1/ops/alerts/{alert_id}/mitigation-preview（Phase 10A）

**201** — アラート連動 COLA 回避試算。衛星 TLE（DB）+ デブリ TLE（catalog）で maneuver preview を実行し `alert_mitigation_previews` に保存。

```json
{
  "direction": "prograde",
  "delta_v_ms": 0.01,
  "duration_days": 7.0,
  "step_minutes": 1
}
```

| フィールド | デフォルト | 備考 |
|-----------|-----------|------|
| `direction` | prograde | prograde / retrograde / normal |
| `delta_v_ms` | 0.01 | m/s |
| `duration_days` | 7.0 | 伝播期間 |
| `step_minutes` | 1 | 刻み |

**監査:** `alert.mitigation_preview`

**404:** デブリ NORAD の TLE が catalog にない場合

### GET /api/v1/ops/alerts/{alert_id}/mitigation-previews（Phase 10A）

試算履歴（新しい順）。`{ "items": [...], "total": N }`

### POST /api/v1/ops/alerts/{alert_id}/mitigation-sweep（Phase 10C）

**201** — Δv 範囲を走査し各試算を DB 保存。best（最小改善 Δv、なければ最大 after_miss）を返す。

```json
{
  "direction": "prograde",
  "delta_v_min_ms": 0.01,
  "delta_v_max_ms": 0.10,
  "delta_v_step_ms": 0.01,
  "max_trials": 20
}
```

**レスポンス:** `{ "items": [...], "best": {...}, "total": N }`

**監査:** `alert.mitigation_sweep`（手動）/ `alert.mitigation_sweep_auto`（screening 自動）

**Phase 10F 拡張:**

- `MitigationPreviewOut.trigger_source` — `manual` | `screening_auto`
- 10E refine 完了後、`AUTO_MITIGATION_SWEEP_ENABLED=true` かつエスカレーション済み（デフォルト）で `mitigation_sweep_task` enqueue
- best preview あり時 `notify_mitigation_best` 追加通知

**環境変数（Phase 10F）:**

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `AUTO_MITIGATION_SWEEP_ENABLED` | `false` | 自動 Δv スイープ |
| `AUTO_MITIGATION_SWEEP_ON_ESCALATION_ONLY` | `true` | エスカレーション済みのみ |
| `AUTO_MITIGATION_SWEEP_PC_MIN` | `1e-5` | ON_ESCALATION_ONLY=false 時の refined Pc 閾値 |

**Phase 10G 拡張:**

- sweep + best 通知後、`AUTO_MITIGATION_PLAN_ENABLED=true` かつ改善 best ありで `maybe_auto_mitigation_plan` → `mitigation_planned`
- optional `AUTO_ACK_BEFORE_MITIGATION_PLAN=true` で `open→acknowledged` 先行
- `notify_mitigation_plan_auto` 追加通知
- `ConjunctionAlertOut.auto_mitigation_planned` — `mitigation_planned` かつ latest preview が `screening_auto`

**環境変数（Phase 10G）:**

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `AUTO_MITIGATION_PLAN_ENABLED` | `false` | 自動対策計画遷移 |
| `AUTO_ACK_BEFORE_MITIGATION_PLAN` | `false` | plan 前に open→ack |

**監査:** `alert.mitigation_plan_auto`

### POST /api/v1/ops/alerts/{alert_id}/mitigation-plan（Phase 10C）

**200** — latest/指定 preview をコメントに含め `mitigation_planned` へ遷移（`acknowledged` のみ）。

```json
{ "preview_id": "optional-uuid", "comment": "任意コメント" }
```

**400:** preview 未存在、または `acknowledged` 以外

**監査:** `alert.mitigation_plan` + `alert.transition`

### POST /api/v1/ops/alerts/{alert_id}/pc-refine（Phase 10D）

**201** — アラート TCA 近傍で Pc を再計算。Space-Track CDM RTN 共分散を優先し、未マッチ時は TLE RTN 異方性共分散でフォールバック。結果を `alert_pc_refinements` に保存（screening `pc` は上書きしない）。

**レスポンス:** `PcRefinementOut` — `pc_screening` / `pc_refined` / `pc_method`（`cdm_rtn` | `tle_rtn`）/ `covariance_source` / `miss_distance_km`

**監査:** `alert.pc_refine`

**404:** デブリ NORAD の TLE が catalog にない場合

### GET /api/v1/ops/alerts/{alert_id}/pc-refinements（Phase 10D）

Pc 再計算履歴（新しい順）。`{ "items": [...], "total": N }`

**レスポンス拡張（Phase 10D）:** `ConjunctionAlertOut.latest_pc_refinement` — 最新 Pc 再計算（なければ null）。screening `pc` と併記。

**Phase 10E 拡張:**

- `PcRefinementOut.trigger_source` — `manual` | `screening_auto`
- `ConjunctionAlertOut.escalated` — 最新 refined Pc が `PC_ESCALATION_PC_MIN` 以上

**環境変数（Phase 10E）:**

| 変数 | デフォルト | 備考 |
|------|-----------|------|
| `AUTO_PC_REFINE_ENABLED` | `false` | スクリーニング新規 open の自動 refine |
| `AUTO_PC_REFINE_PC_MIN` | `1e-5` | 自動 enqueue 閾値（screening Pc） |
| `PC_ESCALATION_PC_MIN` | `1e-5` | エスカレーション通知閾値（refined Pc） |

**Worker:** `refine_alert_pc_task` — screening 後に enqueue。監査 `alert.pc_refine_auto` / `alert.pc_escalate`

### GET /api/v1/ops/sla（Phase 10B）

クエリ: `fleet_id`（任意）。

**200 例:**

```json
{
  "items": [
    {
      "fleet_id": "...",
      "fleet_name": "Ops Fleet",
      "has_active_schedule": true,
      "last_completed_run_at": "2026-06-28T10:00:00Z",
      "screening_lag_seconds": 7200.0,
      "screening_lag_hours": 2.0,
      "screening_sla_ok": true,
      "screening_sla_target_hours": 24.0
    }
  ],
  "overdue_count": 0,
  "screening_sla_target_hours": 24.0,
  "api_availability_ratio": 0.9995,
  "api_availability_percent": 99.95,
  "api_slo_target_percent": 99.9,
  "api_slo_ok": true,
  "api_sample_window_hours": 720.0,
  "api_request_count": 12345
}
```

**Phase 10H 拡張:** トップレベル API SLO フィールドは fleet 非依存（global）。5xx のみエラー、4xx は success。サンプル 0 時 `api_availability_ratio=null`, `api_slo_ok=true`。

**Phase 10N 拡張:** 各 `items[]` に fleet API SLO フィールド（`fleet_api_availability_*`, `fleet_api_slo_ok`, `fleet_api_request_count`）。`SLA_FLEET_API_SLO_ENABLED=true` かつ fleet スコープ API Key リクエストで計上。

- `fleet_id` 指定時: 当該艦隊 1 件（schedule なしでも返す）
- 未指定 + fleet API Key: 自艦隊のみ
- 未指定 + admin / 認証 OFF: active schedule 艦隊すべて

**env:** `SLA_SCREENING_MAX_LAG_HOURS`（default 24）

**env（Phase 10H）:** `SLA_API_TARGET_PERCENT`（default 99.9）, `SLA_API_ROLLING_WINDOW_HOURS`（default 720）

**env（Phase 10J）:** `SLA_API_PERSIST_ENABLED`（default false）, `SLA_API_RETENTION_DAYS`（default 90）

**env（Phase 10K）:** `COV_PROPAGATION_ENABLED`（default false）, `COV_PROP_R_GROWTH_PER_DAY`（default 0.10）, `COV_PROP_T_GROWTH_PER_DAY`（default 0.05）, `COV_PROP_N_GROWTH_PER_DAY`（default 0.05）

**env（Phase 10N）:** `SLA_FLEET_API_SLO_ENABLED`（default false）

### GET /api/v1/ops/sla/api-history（Phase 10J / 10N）

クエリ: `days`（1〜90、default 30）、`fleet_id`（optional、Phase 10N）。UTC 日次 API 可用性 rollup。`fleet_id` 未指定時は global API SLO。

認証: 管理者または認証 OFF（`CAS_API_KEY_REQUIRED=false`）。

```json
{
  "days": 7,
  "target_percent": 99.9,
  "items": [
    {
      "day": "2026-06-28",
      "availability_ratio": 0.999,
      "availability_percent": 99.9,
      "request_count": 1200,
      "errors_5xx": 1,
      "slo_ok": true
    }
  ]
}
```

**DB テーブル（Phase 10J）:** `api_slo_hourly_buckets` — `hour_epoch` PK, `request_total`, `errors_5xx`, `updated_at`

### GET /api/v1/ops/audit（Phase 9E）

クエリ: `fleet_id`（必須）, `limit`, `offset`。alert / TLE / schedule 操作の監査ログ。

---

## API Key 認証（Phase 9E）

**ヘッダ:** `X-API-Key: cas_...`

**env:** `CAS_API_KEY_REQUIRED=false`（デフォルト）— true 時に fleet / screening / ops を保護。ad-hoc 解析 API は公開維持。

| env | 用途 |
|-----|------|
| `CAS_API_KEY_REQUIRED` | true で認証必須 |
| `CAS_ADMIN_API_KEY` | 艦隊作成・初回キー発行 |
| `AUDIT_LOG_RETENTION_DAYS` | 監査ログ保持（default 90） |

### POST /api/v1/fleets/{fleet_id}/api-keys

**201** — 平文キーはこのレスポンスのみ。

```json
{ "name": "ops-key" }
```

### GET /api/v1/fleets/{fleet_id}/api-keys

prefix 一覧（平文は返さない）。

### DELETE /api/v1/fleets/{fleet_id}/api-keys/{key_id}

**204** — 論理 revoke。

---

## OIDC SSO（Phase 10I）

**デフォルト:** `OPS_OIDC_ENABLED=false`

| エンドポイント | 説明 |
|---------------|------|
| `GET /api/v1/auth/oidc/config` | `{ enabled, login_path }` |
| `GET /api/v1/auth/oidc/login` | IdP へリダイレクト |
| `GET /api/v1/auth/oidc/callback` | code 交換 → `cas_ops_session` cookie → `/app/?tab=ops` |
| `POST /api/v1/auth/logout` | セッション cookie 削除 |
| `GET /api/v1/auth/me` | `{ authenticated, email, is_admin, fleet_id }` |

**権限:** `OPS_OIDC_ADMIN_EMAILS` → admin。`OPS_OIDC_FLEET_MAPPINGS` JSON → 艦隊スコープ。`CAS_API_KEY_REQUIRED=true` 時、cookie または `X-API-Key` で ops/fleets/screening 認可。

**監査:** `auth.oidc_login`

**env:**

| 変数 | default | 備考 |
|------|---------|------|
| `OPS_OIDC_ENABLED` | `false` | |
| `OPS_OIDC_ISSUER` | — | |
| `OPS_OIDC_CLIENT_ID` | — | |
| `OPS_OIDC_CLIENT_SECRET` | — | |
| `OPS_OIDC_REDIRECT_URI` | — | |
| `OPS_OIDC_ADMIN_EMAILS` | — | カンマ区切り |
| `OPS_OIDC_FLEET_MAPPINGS` | `{}` | JSON |
| `OPS_SESSION_SECRET` | — | 未設定時 OIDC 無効 |
| `OPS_SESSION_TTL_HOURS` | `8` | |

---

## Pydantic モデル対応表

| モデル | ファイル |
|--------|---------|
| ConjunctionsRequest | `backend/app/models/schemas.py` |
| ConjunctionsResponse | 同上 |
| CdmParseRequest / CdmRecordOut | 同上 |
| CdmCompareRequest / CdmCompareResponse | 同上 |
| BatchConjunctionsRequest / BatchConjunctionsResponse | 同上 |
| FleetCreate / FleetOut / SatelliteCreate / SatelliteOut | 同上 |
| ScreeningScheduleCreate / ScreeningRunOut | 同上 |
| ConjunctionAlertOut / FleetOpsSummaryOut | 同上 |
| OrbitRequest / OrbitResponse | 同上 |
| ManeuverPreviewRequest / ManeuverPreviewResponse | 同上 |

---

## OpenAPI

起動後 `http://127.0.0.1:8000/docs` で Swagger UI を参照。
