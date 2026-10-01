
CREATE OR REPLACE TABLE `tfl-data-pipeline-stg.core.core_tfl__disruptions__weather` AS

WITH disruptions AS (
  SELECT
    disruption_key,
    last_update,
    description,
    type,
    category,
    affectedStops,
    created,
    TIMESTAMP_TRUNC(created, HOUR) AS created_hour
  FROM `tfl-data-pipeline-stg.staging.stg_tfl__disruptions`
),

weather AS (
  SELECT
    weather_hour, 
    temperature_2m, 
    precipitation, 
    wind_speed_10m, 
    relative_humidity_2m
  FROM `tfl-data-pipeline-stg.staging.stg_weather__hourly`

)

SELECT
 d.disruption_key,
  d.created,
  d.last_update,
  d.description,
  d.type,
  d.category,
  d.affectedStops,
  w.weather_hour,
  w.temperature_2m,
  w.precipitation,
  w.wind_speed_10m
FROM disruptions d
LEFT JOIN weather w 
ON d.created_hour = w.weather_hour