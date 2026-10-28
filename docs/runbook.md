# Runbook – TFL Analytics Pipeline

## Deploy ingestion

Each script in `ingestion/` is a Cloud Run service using the Functions Framework entry point `main(request)`. Ingestion is deployed to **prod only** (`tfl-data-pipeline`); lower environments read prod's `landing` dataset.

```bash
PROJECT=tfl-data-pipeline
REGION=europe-west2
SA=cloud-run@${PROJECT}.iam.gserviceaccount.com

# TfL disruptions
gcloud run deploy tfl-disruptions-ingest \
  --project $PROJECT --region $REGION \
  --source ingestion --entry-point main \
  --service-account $SA \
  --set-env-vars TFL_BUCKET_NAME=tfl-data-pipeline-raw \
  --set-secrets TFL_APP_KEY=tfl-app-key:latest \
  --no-allow-unauthenticated

# Weather
gcloud run deploy weather-ingest \
  --project $PROJECT --region $REGION \
  --source ingestion --entry-point main \
  --service-account $SA \
  --set-env-vars WEATHER_BUCKET_NAME=tfl-data-pipeline-raw \
  --no-allow-unauthenticated
```

> **TODO:** confirm the actual deploy layout. `--source` with `--entry-point` expects a `main.py` and `functions-framework` in `requirements.txt`; with two scripts in one folder, either split `ingestion/` into `ingestion/tfl/` and `ingestion/weather/` or deploy a container with the script name as the command.

## Schedule

```bash
gcloud scheduler jobs create http tfl-disruptions-hourly \
  --project $PROJECT --location $REGION \
  --schedule "0 * * * *" \
  --uri "$(gcloud run services describe tfl-disruptions-ingest --region $REGION --format 'value(status.url)')" \
  --oidc-service-account-email $SA

gcloud scheduler jobs create http weather-hourly \
  --project $PROJECT --location $REGION \
  --schedule "5 * * * *" \
  --uri "$(gcloud run services describe weather-ingest --region $REGION --format 'value(status.url)')" \
  --oidc-service-account-email $SA
```

## Manual trigger

```bash
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "$(gcloud run services describe tfl-disruptions-ingest --region $REGION --format 'value(status.url)')"
```

## Scheduled queries

Transformations run as BigQuery scheduled queries (Data Transfer Service) in `tfl-data-pipeline-stg`, region `us-central1`. See the orchestration table in the README for cadence. To inspect runs:

```sql
SELECT creation_time, statement_type, destination_table.table_id, state, error_result.message
FROM `tfl-data-pipeline-stg`.`region-us-central1`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE EXISTS (SELECT 1 FROM UNNEST(labels) l WHERE l.key = 'data_source_id')
  AND creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
ORDER BY creation_time DESC;
```

To change a transformation: edit the file in `sql/`, open the scheduled query in the BigQuery console → Scheduled queries → Edit, paste the new SQL. There is no automated sync.

## Run transformations manually

Order matters. Run against the target environment's project.

1. **First time only** — bootstraps:
   - `sql/staging/tfl/stg_tfl__disruptions_bootstrap.sql`
   - `sql/staging/tfl/stg_tfl__disruptions__history_bootstrap.sql`
2. **Every run:**
   - `sql/staging/tfl/stg_tfl__disruptions_merge.sql`
   - `sql/staging/tfl/stg_tfl__disruptions__history_insert.sql`
   - `sql/staging/weather/stg_weather__hourly_bootstrap.sql` (full rebuild)
   - `sql/core/core_tfl__disruptions__weather.sql` (full rebuild)

```bash
bq query --project_id=tfl-data-pipeline-stg --use_legacy_sql=false < sql/staging/tfl/stg_tfl__disruptions_merge.sql
```

The MERGE and history INSERT are idempotent: re-running them does not duplicate rows. Both read only the last 7 days of `landing` by `fetched_at`.

## Backfill

Raw files in GCS are immutable, so any window can be replayed.

1. Load the GCS files for the window into the landing table (or widen the external table's path filter).
2. Edit the `fetched_at >= TIMESTAMP_SUB(..., INTERVAL 7 DAY)` filter in the MERGE and history INSERT to cover the window, run them, then revert.
3. Re-run the weather and core rebuilds; they always read the full landing table.

## Checks

```sql
-- staging key uniqueness
SELECT disruption_key, COUNT(*) c
FROM `tfl-data-pipeline-stg.staging.stg_tfl__disruptions`
GROUP BY 1 HAVING c > 1;

-- history: one row per (key, last_update)
SELECT disruption_key, last_update, COUNT(*) c
FROM `tfl-data-pipeline-stg.staging.stg_tfl__disruptions__history`
GROUP BY 1, 2 HAVING c > 1;

-- ingestion freshness
SELECT MAX(fetched_at) FROM `tfl-data-pipeline.landing.tfl-disruptions-raw`;
```

## Known gaps

- No landing external-table DDL in the repo yet.
- Scheduled-query SQL is pasted by hand from `sql/`; nothing enforces that they match.
- Weather and core are full rebuilds; convert to MERGE when volume warrants.
- No reject table; uncastable rows are silently dropped at staging.
