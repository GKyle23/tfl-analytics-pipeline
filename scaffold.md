# Scaffold & Environment Setup – TFL Analytics Pipeline

This document describes the initial environment structure, naming conventions, and baseline setup for the TFL Analytics Pipeline.

---

## 1. Overview

The pipeline ingests Transport for London (TFL) disruption data, enriches it with weather information, stores raw data in GCS and BigQuery, transforms and aggregates it in BigQuery, and serves insights via Looker.  
Cloud Composer (Airflow) orchestrates ingestion, transformation, and loading tasks. Jupyter is used for development and QA only.

---

## 2. GCP Project Structure

 **separate projects per environment** are used for isolation, billing clarity, and IAM control.

| Environment | GCP Project ID | Purpose |
|-------------|---------------|---------|
| **Dev**     | `tfl-analytics-dev`     | Development, feature testing, schema changes |
| **Staging** | `tfl-analtytic-stg`     | Pre-production validation |
| **Prod**    | `tfl-analytics-prod`    | Production data pipeline |


---

## 3. Composer Environments

Each environment has a dedicated **Cloud Composer** instance.

| Env | Composer Name       | Region         | Airflow Version |
|-----|---------------------|----------------|-----------------|
| Dev | `composer-tfl-dev`  | `europe-west2` | 2.x.x           |
| Stg | `composer-tfl-stg`  | `europe-west2` | 2.x.x           |
| Prod| `composer-tfl-prod` | `europe-west2` | 2.x.x           |

---

## 4. GCS Buckets

Buckets are environment-specific.  
Folder structure supports partitioned storage by ingestion date.

gs://tfl-<env>-raw/tfl/YYYY/MM/DD/
gs://tfl-<env>-raw/weather/YYYY/MM/DD/

yaml
Copy
Edit

Examples:
- `gs://tfl-dev-raw/tfl/2025/08/11/disruptions_2025-08-11T14:00:00Z.json`
- `gs://tfl-dev-raw/weather/2025/08/11/weather_2025-08-11T14:00:00Z.json`

---

## 5. BigQuery Datasets & Tables

A **layered ELT** approach:

| Dataset    | Purpose | Example Tables |
|------------|---------|----------------|
| `raw`      | Immutable API ingestions | `raw_disruptions`, `raw_weather` |
| `stg`      | Cleaned and typed | `stg_disruptions`, `stg_weather` |
| `enriched` | Joined datasets | `enriched_disruptions` |
| `prod`     | Aggregations for BI | `summary_disruption_metrics` |

**Partitioning:** All raw/staging tables partitioned by `fetched_at` (ingestion timestamp).  
**Clustering:** By high-cardinality fields (e.g., `line_id`, `category`).

---

## 6. Secrets

Stored in **Secret Manager**, one per environment:

| Secret Name         | Purpose |
|---------------------|---------|
| `tfl_api_key`       | TFL API key |
| `weather_api_key`   | Weather API key |

Access granted only to the Composer service account in that environment.

---

## 7. Branching & Deployment

- **`dev` branch** → deploys to `tfl-dev` Composer
- **`staging` branch** → deploys to `tfl-stg` Composer
- **`main` branch** → deploys to `tfl-prod` Composer

Deployment is handled via Cloud Build:
1. On branch push, sync `/dags` to the matching Composer bucket.
2. Apply any schema changes using BigQuery operators or migration scripts.

---

## 8. IAM Overview

**Service accounts**:
- `airflow@tfl-<env>.iam.gserviceaccount.com`
  - Roles: BigQuery Job User, BigQuery Data Editor (env datasets), Storage Object Admin (env bucket), Secret Manager Secret Accessor (env secrets only).

---


## 9. Runbook References

- [Runbook](runbook.md) — operational procedures (backfills, reruns, failure handling)
- [Data Model Dictionary](data_model.md) — table definitions and field descriptions


