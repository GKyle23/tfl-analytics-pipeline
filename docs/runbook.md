# Runbook – TFL Analytics Pipeline

## Ingestion

Ingestion runs in **prod only** (`tfl-data-pipeline`); lower environments read prod's `landing` dataset. Each script in `ingestion/` is its own Cloud Run service (Functions Framework, entry point `main`), built by its own Cloud Build trigger and called by its own Cloud Scheduler job.

| Feed | Source file | Service (europe-west1) | Trigger (europe-west2) | Scheduler job (us-central1) | Cadence (UTC) | Writes |
|---|---|---|---|---|---|---|
| TfL disruptions | `ingestion/tfl_disruptions.py` | `tfl-analytics-pipeline` | `…-GKyle23-tfl` | `tfl-fetch-schedule` | every 30 min | `gs://tfl-data-pipeline-raw/tfl_disruptions/YYYY/MM/DD/HH/` |
| Weather | `ingestion/weather.py` | `weather-ingest` | `…-GKyle23-weather` | `weather-fetch-schedule` | hourly at :05 | `gs://weather-data-pipeline-raw/weather_forecast_data/YYYY/MM/DD/HH/` |

Full trigger names are `rmgpgab-tfl-analytics-pipeline-europe-west1-GKyle23-tfl` and `…-weather`. The TfL service kept the original service name (`tfl-analytics-pipeline`), which is also the repo name, so don't read it as covering both feeds.

### How a deploy works

Both triggers fire on a push to `main` that touches `ingestion/**`, `requirements.txt` or `runtime.txt` (`includedFiles`). Changes to `dbt/`, `sql/`, `docs/` or `tests/` do not redeploy ingestion. Each trigger runs the same three build steps:

1. `pack build` with `GOOGLE_FUNCTION_SOURCE=ingestion/<script>.py` and `GOOGLE_FUNCTION_TARGET=main` (the buildpack picks which file the service runs).
2. Push the image to Artifact Registry (`cloud-run-source-deploy`).
3. `gcloud run services update $_SERVICE_NAME`.

The live trigger configs are saved in `infra/cloudbuild/` (`tfl-trigger.yaml`, `weather-trigger.yaml`); edit the file and re-import it with `gcloud builds triggers import` (command in each file's header) rather than hand-editing in the console, so the repo stays the record.

`$_SERVICE_NAME` is a trigger substitution. **The two triggers must never share a service name.** Until Nov 2026 both deployed to `tfl-analytics-pipeline`, so every push started two builds that overwrote each other and the last one to finish decided whether TfL or weather ran. That caused two multi-week gaps (weather 28 Oct to 19 Nov, TfL 19 Nov to 25 Nov).

Both services run with `976003765037-compute@developer.gserviceaccount.com`, ingress `internal`, no unauthenticated access. The Scheduler jobs call them with an OIDC token from `tfl-pipeline-sa@tfl-data-pipeline.iam.gserviceaccount.com` (`roles/run.invoker` at project level).

Env vars: TfL service `TFL_APP_KEY`, `TFL_BUCKET_NAME`, `WEATHER_BUCKET_NAME`; weather service `WEATHER_BUCKET_NAME`.

### Deploy by hand

```bash
PROJECT=tfl-data-pipeline

# Build and deploy the current main (ignores the file filter)
gcloud builds triggers run <trigger-id> --project $PROJECT --region europe-west2 --branch main
gcloud builds triggers list --project $PROJECT --region europe-west2 --format="value(name,id)"
```

### Roll back

```bash
gcloud run revisions list --service <service> --region europe-west1 --project $PROJECT
gcloud run services update-traffic <service> --region europe-west1 --project $PROJECT \
  --to-revisions <revision>=100
```

A later push will move traffic to the newest revision again.

### Run a feed now

The services use `internal` ingress, so `curl` from a laptop is rejected. Run the Scheduler job instead:

```bash
gcloud scheduler jobs run tfl-fetch-schedule     --project $PROJECT --location us-central1
gcloud scheduler jobs run weather-fetch-schedule --project $PROJECT --location us-central1
```

### Check a feed is healthy

```bash
# newest TfL file should be under 30 minutes old
gcloud storage ls -l -r "gs://tfl-data-pipeline-raw/tfl_disruptions/$(date -u +%Y/%m/%d)/" | tail -2
# newest weather file should be under an hour old
gcloud storage ls -l -r "gs://weather-data-pipeline-raw/weather_forecast_data/$(date -u +%Y/%m/%d)/" | tail -2
```

A `200` from the Scheduler job does not prove a feed works: it only means the service answered. If a feed goes quiet, check which function the service runs: `>>> ENTERED UPLOAD` in the logs is TfL, `Fetching weather data` is weather. Landing's newest `fetched_at` is the quickest staleness signal (see Checks below).

## Deploy dbt (Cloud Run Job)

dbt runs as a Cloud Run **Job** (not a service: it runs `dbt build` to completion and exits). The `cloud` target in `dbt/profiles.yml` reads `DBT_GCP_PROJECT` and writes each model to its `+schema` (`staging`, ...) using the job's service account. `dev` (the default) writes everything to `dbt_dev` using your own login. See `dbt/macros/generate_schema_name.sql`.

**Status:** the job `dbt-build` exists in `tfl-data-pipeline-stg` (`us-central1`) and has been run by hand successfully (8/8 passing: 1 model, 7 tests). It is **not scheduled yet** and runs a one-off `:test` image, not a pinned build.

```bash
PROJECT=tfl-data-pipeline-stg        # project dbt writes to
REGION=us-central1                   # must match the BigQuery dataset location
SA=dbt-runner@${PROJECT}.iam.gserviceaccount.com
IMAGE=${REGION}-docker.pkg.dev/${PROJECT}/dbt/dbt-build
```

### One-time setup (already done)

APIs `artifactregistry`, `cloudbuild` and `run` are enabled, and an Artifact Registry Docker repo `dbt` exists in `us-central1`.

```bash
gcloud iam service-accounts create dbt-runner --project $PROJECT
gcloud projects add-iam-policy-binding $PROJECT \
  --member serviceAccount:$SA --role roles/bigquery.jobUser
# Landing tables are EXTERNAL tables over a prod bucket, so the account needs
# read on the bucket as well as on the dataset:
gcloud storage buckets add-iam-policy-binding gs://tfl-data-pipeline-raw \
  --member serviceAccount:$SA --role roles/storage.objectViewer
```

Dataset-level grants are done with SQL, because it works without the `bq` CLI and needs the dataset location set. Add `core` and `mart` the same way when models land there:

```sql
SET @@location = 'us-central1';
GRANT `roles/bigquery.dataEditor` ON SCHEMA `tfl-data-pipeline-stg.staging`
  TO "serviceAccount:dbt-runner@tfl-data-pipeline-stg.iam.gserviceaccount.com";
GRANT `roles/bigquery.dataViewer` ON SCHEMA `tfl-data-pipeline.landing`
  TO "serviceAccount:dbt-runner@tfl-data-pipeline-stg.iam.gserviceaccount.com";
```

The datasets in `tfl-data-pipeline-stg` are `staging`, `core`, `mart` (singular, unlike the README's `marts`) and `dbt_dev`. If you add weather sources to dbt, also grant `storage.objectViewer` on `gs://weather-data-pipeline-raw`.

### Build and deploy

```bash
TAG=$(git rev-parse --short HEAD)
gcloud builds submit dbt --project $PROJECT --tag $IMAGE:$TAG

# first time
gcloud run jobs create dbt-build --project $PROJECT --region $REGION \
  --image $IMAGE:$TAG --service-account $SA \
  --set-env-vars DBT_GCP_PROJECT=$PROJECT,DBT_BQ_LOCATION=$REGION \
  --max-retries 0 --task-timeout 15m

# afterwards
gcloud run jobs update dbt-build --project $PROJECT --region $REGION --image $IMAGE:$TAG
```

Tag by commit so you can roll back with `jobs update --image $IMAGE:<older-tag>`. Nothing rebuilds this image automatically yet (see Known gaps).

### Run

```bash
gcloud run jobs execute dbt-build --project $PROJECT --region $REGION --wait
```

Logs are in Cloud Logging under the job. A failing test fails the job, which shows as a failed execution. To run the same project locally: `cd dbt && dbt build` (uses `dev` and `dbt_dev`).

### Schedule (not created yet)

Same cadence as the legacy merge (:12 and :42):

```bash
gcloud scheduler jobs create http dbt-build-30min \
  --project $PROJECT --location $REGION \
  --schedule "12,42 * * * *" \
  --uri "https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/dbt-build:run" \
  --http-method POST \
  --oauth-service-account-email $SA
gcloud run jobs add-iam-policy-binding dbt-build --project $PROJECT --region $REGION \
  --member serviceAccount:$SA --role roles/run.invoker
```

### Cutover from the legacy query

The model writes `staging.stg_tfl__disruptions_merge`, a separate table from the legacy `staging.stg_tfl__disruptions`, so the two can run side by side. They are not equivalent yet:

- The legacy table has duplicate keys from its bootstrap load (e.g. 168 rows per key, all with the same `stg_loaded_at`); the dbt table has one row per `disruption_key`, enforced by a `unique` test.
- The dbt model coalesces `fetched_at` to `created` for about 4,000 historical landing rows that predate the column; the legacy SQL does not.
- Check what the core weather join does with duplicate rows before switching it to the dbt table, then disable the legacy scheduled query and rename the model or give it an `alias`.

### `bq` CLI on Windows (Git Bash)

If `bq` fails with `python3.14: command not found`, set `CLOUDSDK_PYTHON` to the real interpreter (a user environment variable, plus `export CLOUDSDK_PYTHON=...` in `~/.bashrc` for Git Bash). PowerShell is unaffected.

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
- The dbt image is built by hand (`gcloud builds submit`) and the job is unscheduled; there is no CI running `dbt build` on pull requests and nothing redeploys the job on merge.
- `TFL_APP_KEY` is a plain-text environment variable on the TfL service. Move it to Secret Manager (`--set-secrets`) and rotate the key.
- The ingestion triggers can't tell you a feed has gone quiet: add an alert on landing freshness (`MAX(fetched_at)`) so a stalled feed is noticed in hours, not days.
- The legacy `staging.stg_tfl__disruptions` has duplicate keys from its bootstrap load.
