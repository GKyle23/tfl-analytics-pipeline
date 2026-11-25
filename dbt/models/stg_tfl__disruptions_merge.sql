{{
    config(
        materialized='incremental',
        unique_key='disruption_key',
        incremental_strategy='merge',
        partition_by={
            'field': 'created',
            'data_type': 'timestamp',
            'granularity': 'day'
        }
    )
}}

/*
Current-state staging table: one row per disruption_key, upserted from the
landing raw table. disruption_key makes re-runs idempotent.

Partitioned by DATE(created) (day granularity on the TIMESTAMP column).
Incremental runs read only the last 7 days of landing by fetched_at.
*/

WITH source AS (

    SELECT * FROM {{ source('landing', 'tfl_disruptions_raw') }}

),

cleaned AS (

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
        -- ~4,000 historical landing rows pre-date fetched_at; fall back to created
        COALESCE(fetched_at, SAFE_CAST(created AS TIMESTAMP)) AS fetched_at,
        CURRENT_TIMESTAMP()              AS stg_loaded_at

    FROM source

    WHERE SAFE_CAST(created AS TIMESTAMP) IS NOT NULL

    {% if is_incremental() %}
      AND fetched_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    {% endif %}

)

SELECT *
FROM cleaned
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY disruption_key
    ORDER BY last_update DESC, fetched_at DESC
) = 1
