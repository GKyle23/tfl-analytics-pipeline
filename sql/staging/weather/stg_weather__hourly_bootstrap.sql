CREATE OR REPLACE TABLE `tfl-data-pipeline-stg.staging.stg_weather__hourly`
PARTITION BY DATE(weather_hour)
AS
SELECT
  time                                         AS weather_hour,
  -- Open-Meteo returns past_days + forecast_days in one payload; rows whose
  -- hour is later than the fetch are forecasts, not observations.
  time > SAFE_CAST(fetched_at AS TIMESTAMP)    AS is_forecast,
  SAFE_CAST(temperature_2m AS FLOAT64)         AS temperature_2m,
  SAFE_CAST(precipitation AS FLOAT64)          AS precipitation,
  SAFE_CAST(wind_speed_10m AS FLOAT64)         AS wind_speed_10m,
  SAFE_CAST(relative_humidity_2m AS FLOAT64)   AS relative_humidity_2m,
  SAFE_CAST(latitude AS FLOAT64)               AS latitude,
  SAFE_CAST(longitude AS FLOAT64)              AS longitude,
  SAFE_CAST(fetched_at AS TIMESTAMP)           AS fetched_at,
  CURRENT_TIMESTAMP()                          AS stg_loaded_at
FROM `tfl-data-pipeline.landing.weather-raw`
WHERE time IS NOT NULL
-- Prefer the latest fetch per hour, but an observation always beats a forecast.
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY time
  ORDER BY is_forecast ASC, SAFE_CAST(fetched_at AS TIMESTAMP) DESC
) = 1;