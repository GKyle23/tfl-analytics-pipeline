CREATE TABLE `tfl-data-pipeline-stg.staging.stg_tfl__disruptions__history`
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

  history_loaded_at TIMESTAMP
)
PARTITION BY DATE(fetched_at)
CLUSTER BY disruption_key;