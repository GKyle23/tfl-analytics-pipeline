CREATE OR REPLACE TABLE `tfl-data-pipeline-stg.landing.stg_tfl__disruptions__raw`
PARTITION BY DATE(created)
AS
SELECT
  -- Stable primary key
  TO_HEX(SHA256(
    CONCAT(
      CAST(SAFE_CAST(created AS TIMESTAMP) AS STRING),
      '|',
      LOWER(TRIM(description)),
      '|',
      LOWER(TRIM(type))
    )
  )) AS disruption_key,

  -- Core fields
  SAFE_CAST(created AS TIMESTAMP)     AS created,
  SAFE_CAST(lastUpdate AS TIMESTAMP)  AS last_update,
  LOWER(TRIM(description))            AS description,
  LOWER(TRIM(category))               AS category,
  LOWER(TRIM(type))                   AS type,

  -- Optional
  SAFE_CAST(closureText AS STRING)    AS closure_text,

  -- Arrays
  affectedRoutes,
  affectedStops,

  -- Metadata
  meta_type,

  -- ✅ ADD THIS
  SAFE_CAST(fetched_at AS TIMESTAMP)  AS fetched_at,

  -- Lineage
  CURRENT_TIMESTAMP() AS stg_loaded_at

FROM `tfl-data-pipeline.landing.tfl-disruptions-raw`

WHERE SAFE_CAST(created AS TIMESTAMP) IS NOT NULL;