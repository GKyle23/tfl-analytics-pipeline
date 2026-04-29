CREATE OR REPLACE TABLE `tfl-data-pipeline-stg.landing.stg_tfl__disruptions`
(
  disruption_key STRING,
  created TIMESTAMP,
  last_update TIMESTAMP,
  description STRING,
  category STRING,
  type STRING,
  closure_text STRING,
  affectedRoutes ARRAY<STRING>,
  affectedStops ARRAY<STRING>,
  meta_type STRING,
  fetched_at TIMESTAMP,
  stg_loaded_at TIMESTAMP
)
PARTITION BY DATE(created);