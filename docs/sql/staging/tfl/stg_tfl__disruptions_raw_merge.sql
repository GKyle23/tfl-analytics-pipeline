
/*
This SQL script is to faciliate a merge from the landing raw table into the staging table.
Note I am creating a unique key here to faciliate idempotence. This approach
gives an "updated" view in th data as disruptions update over time.
*/


MERGE `tfl-data-pipeline-stg.staging.stg_tfl__disruptions` T
USING (
  SELECT *
  FROM (
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

      SAFE_CAST(created AS TIMESTAMP)     AS created,
      SAFE_CAST(lastUpdate AS TIMESTAMP)  AS last_update,
      LOWER(TRIM(description))            AS description,
      LOWER(TRIM(category))               AS category,
      LOWER(TRIM(type))                   AS type,
      SAFE_CAST(closureText AS STRING)    AS closure_text,

      affectedRoutes,
      affectedStops,
      meta_type,
      fetched_at,

      CURRENT_TIMESTAMP() AS stg_loaded_at

    FROM `tfl-data-pipeline.landing.tfl-disruptions-raw`

    WHERE SAFE_CAST(created AS TIMESTAMP) IS NOT NULL
      AND fetched_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  )
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY disruption_key
    ORDER BY last_update DESC, fetched_at DESC
  ) = 1
) S

ON T.disruption_key = S.disruption_key

WHEN MATCHED AND T.last_update != S.last_update THEN
  UPDATE SET
    created        = S.created,
    last_update    = S.last_update,
    description    = S.description,
    category       = S.category,
    type           = S.type,
    closure_text   = S.closure_text,
    affectedRoutes = S.affectedRoutes,
    affectedStops  = S.affectedStops,
    meta_type      = S.meta_type,
    fetched_at     = S.fetched_at,
    stg_loaded_at  = S.stg_loaded_at

WHEN NOT MATCHED THEN
  INSERT (
    disruption_key,
    created,
    last_update,
    description,
    category,
    type,
    closure_text,
    affectedRoutes,
    affectedStops,
    meta_type,
    fetched_at,
    stg_loaded_at
  )
  VALUES (
    S.disruption_key,
    S.created,
    S.last_update,
    S.description,
    S.category,
    S.type,
    S.closure_text,
    S.affectedRoutes,
    S.affectedStops,
    S.meta_type,
    S.fetched_at,
    S.stg_loaded_at
  );