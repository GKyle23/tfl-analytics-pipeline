/*
Inserts new disruption versions into the history table.
A row is added only when a (disruption_key, last_update) pair hasn't been seen before,
so history records each change TfL makes, not every fetch.
*/

INSERT INTO `tfl-data-pipeline-stg.staging.stg_tfl__disruptions__history`
  (disruption_key, created, last_update, description, category, type,
   closure_text, affectedRoutes, affectedStops, meta_type, fetched_at,
   history_loaded_at)

WITH src AS (
  SELECT
    TO_HEX(SHA256(CONCAT(
      CAST(SAFE_CAST(created AS TIMESTAMP) AS STRING), '|',
      LOWER(TRIM(description)), '|',
      LOWER(TRIM(type))
    ))) AS disruption_key,
    SAFE_CAST(created AS TIMESTAMP)    AS created,
    SAFE_CAST(lastUpdate AS TIMESTAMP) AS last_update,
    LOWER(TRIM(description))           AS description,
    LOWER(TRIM(category))              AS category,
    LOWER(TRIM(type))                  AS type,
    SAFE_CAST(closureText AS STRING)   AS closure_text,
    affectedRoutes,
    affectedStops,
    meta_type,
    fetched_at
  FROM `tfl-data-pipeline.landing.tfl-disruptions-raw`
  WHERE SAFE_CAST(created AS TIMESTAMP) IS NOT NULL
   AND fetched_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  -- collapse repeat fetches of the same version within this batch
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY disruption_key, last_update
    ORDER BY fetched_at ASC
  ) = 1
)

SELECT
  s.disruption_key,
  s.created,
  s.last_update,
  s.description,
  s.category,
  s.type,
  s.closure_text,
  s.affectedRoutes,
  s.affectedStops,
  s.meta_type,
  s.fetched_at,
  CURRENT_TIMESTAMP() AS history_loaded_at
FROM src s
WHERE NOT EXISTS (
  SELECT 1
  FROM `tfl-data-pipeline-stg.staging.stg_tfl__disruptions__history` h
  WHERE h.disruption_key = s.disruption_key
    AND h.last_update = s.last_update
);