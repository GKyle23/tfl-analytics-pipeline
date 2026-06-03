/*
Tihs SQL inserts data into the history table.
*/



INSERT INTO `tfl-data-pipeline-stg.staging.stg_tfl__disruptions__history`

SELECT
  TO_HEX(
    SHA256(
      CONCAT(
        CAST(SAFE_CAST(created AS TIMESTAMP) AS STRING),
        '|',
        LOWER(TRIM(description)),
        '|',
        LOWER(TRIM(type))
      )
    )
  ) AS disruption_key,

  SAFE_CAST(created AS TIMESTAMP) AS created,
  SAFE_CAST(lastUpdate AS TIMESTAMP) AS last_update,

  LOWER(TRIM(description)) AS description,
  LOWER(TRIM(category)) AS category,
  LOWER(TRIM(type)) AS type,

  SAFE_CAST(closureText AS STRING) AS closure_text,

  affectedRoutes,
  affectedStops,

  meta_type,

  fetched_at,

  CURRENT_TIMESTAMP() AS history_loaded_at

FROM `tfl-data-pipeline.landing.tfl-disruptions-raw`

WHERE SAFE_CAST(created AS TIMESTAMP) IS NOT NULL
  AND fetched_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)

  AND NOT EXISTS (
  SELECT 1
  FROM `tfl-data-pipeline-stg.staging.stg_tfl__disruptions__history` h
  WHERE h.disruption_key = TO_HEX(
      SHA256(
        CONCAT(
          CAST(SAFE_CAST(created AS TIMESTAMP) AS STRING),
          '|',
          LOWER(TRIM(description)),
          '|',
          LOWER(TRIM(type))
        )
      )
    )
    AND h.fetched_at = fetched_at
)