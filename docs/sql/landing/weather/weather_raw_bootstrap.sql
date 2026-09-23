-- Replace PROJECT_ID and WEATHER_BUCKET_NAME for the target environment.
-- Keep the BigQuery dataset and GCS bucket in compatible locations.
-- Source: weather_forecast_data/YYYY/MM/DD/HH/weather_data.ndjson
CREATE OR REPLACE EXTERNAL TABLE `PROJECT_ID.landing.weather_raw` (
  fetched_at STRING,
  time STRING,
  temperature_2m FLOAT64,
  precipitation FLOAT64,
  wind_speed_10m FLOAT64,
  relative_humidity_2m FLOAT64,
  latitude FLOAT64,
  longitude FLOAT64
)
OPTIONS (
  format = 'NEWLINE_DELIMITED_JSON',
  uris = ['gs://WEATHER_BUCKET_NAME/weather_forecast_data/*'],
  max_bad_records = 0
);

-- Smoke check once at least one hourly NDJSON file exists:
-- SELECT COUNT(*) AS hourly_rows,
--        MIN(SAFE_CAST(time AS TIMESTAMP)) AS first_hour_utc,
--        MAX(SAFE_CAST(time AS TIMESTAMP)) AS last_hour_utc
-- FROM `PROJECT_ID.landing.weather_raw`;
