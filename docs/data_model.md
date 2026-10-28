# Data Model – TFL Analytics Pipeline

All tables live in `tfl-data-pipeline-<env>` except `landing`, which lives only in prod (`tfl-data-pipeline`). See [scaffold.md](scaffold.md) §2.

## Lineage

```
landing.tfl-disruptions-raw ──┬──> staging.stg_tfl__disruptions ──────────┐
                              └──> staging.stg_tfl__disruptions__history   ├──> core.core_tfl__disruptions__weather
landing.weather-raw ───────────────> staging.stg_weather__hourly ──────────┘
```

## Keys

**`disruption_key`** = `SHA256(created | lower(trim(description)) | lower(trim(type)))`, hex-encoded.

The TfL disruption endpoint has no stable id. `created` + `type` + `description` is the best available natural key. Known limitation: if TfL edits a description in place, the hash changes and the disruption appears as a new row; the old row is never updated or closed.

## `staging.stg_tfl__disruptions`

Current state. One row per `disruption_key`, upserted by `stg_tfl__disruptions_merge.sql`. Partition: `DATE(created)`.

| Column | Type | Source | Notes |
|---|---|---|---|
| `disruption_key` | STRING | derived | PK, see Keys |
| `created` | TIMESTAMP | `created` | Event time; rows with uncastable `created` are dropped |
| `last_update` | TIMESTAMP | `lastUpdate` | Nullable; drives MERGE update condition |
| `description` | STRING | `description` | Lower-cased, trimmed |
| `category` | STRING | `category` | Lower-cased, trimmed (e.g. `realtime`, `plannedwork`) |
| `type` | STRING | `type` | Lower-cased, trimmed (e.g. `lineinfo`, `routeinfo`) |
| `closure_text` | STRING | `closureText` | Nullable |
| `affectedRoutes` | ARRAY<STRING> | `affectedRoutes` | Passed through as-is |
| `affectedStops` | ARRAY<STRING> | `affectedStops` | Passed through as-is |
| `meta_type` | STRING | `$type` | TfL API type URI |
| `fetched_at` | TIMESTAMP | ingestion | When the API was called |
| `stg_loaded_at` | TIMESTAMP | derived | When this row was last written |

## `staging.stg_tfl__disruptions__history`

Change log. One row per `(disruption_key, last_update)`, appended by `stg_tfl__disruptions__history_insert.sql`. A row is added only when that pair has not been seen before, so repeat fetches of an unchanged disruption do not add rows. Partition: `DATE(fetched_at)`; cluster: `disruption_key`.

Same columns as `stg_tfl__disruptions`, with `history_loaded_at` in place of `stg_loaded_at`. `fetched_at` is the first fetch that saw this version.

## `staging.stg_weather__hourly`

One row per hour at London (51.5072, -0.1276). Rebuilt in full by `stg_weather__hourly_bootstrap.sql`. Partition: `DATE(weather_hour)`.

Open-Meteo returns `past_days=1` + `forecast_days=1` in each hourly fetch, so every hour is captured many times. Dedupe keeps one row per hour, preferring an observation (`is_forecast = false`) over any forecast, then the latest fetch.

| Column | Type | Notes |
|---|---|---|
| `weather_hour` | TIMESTAMP | PK; UTC |
| `is_forecast` | BOOL | `weather_hour > fetched_at` |
| `temperature_2m` | FLOAT64 | °C |
| `precipitation` | FLOAT64 | mm |
| `wind_speed_10m` | FLOAT64 | km/h |
| `relative_humidity_2m` | FLOAT64 | % |
| `latitude`, `longitude` | FLOAT64 | |
| `fetched_at` | TIMESTAMP | Fetch that supplied this row |
| `stg_loaded_at` | TIMESTAMP | |

## `core.core_tfl__disruptions__weather`

One row per disruption, left-joined to observed weather for the hour the disruption was created (`TIMESTAMP_TRUNC(created, HOUR) = weather_hour AND NOT is_forecast`). Rebuilt in full by `core_tfl__disruptions__weather.sql`.

Columns: `disruption_key`, `created`, `last_update`, `description`, `type`, `category`, `affectedStops`, `weather_hour`, `temperature_2m`, `precipitation`, `wind_speed_10m`. Weather columns are NULL when no observation exists for that hour yet.
