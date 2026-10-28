 Scaffold & Environment Setup – TFL Analytics Pipeline

This document defines the environment structure, naming conventions, and baseline setup for the **TFL Analytics Pipeline (WIP)**.

---

## 1. Overview

This pipeline ingests Transport for London (TFL) disruption data and enriches it with weather data to make it analytics-ready in BigQuery.

**Key principles:**
- ELT-first (BigQuery does the heavy lifting)
- Simple, serverless orchestration (Cloud Run + scheduled triggers)
- Clear dataset layering for analytics engineering workflows
- Designed as a portfolio-grade analytics engineering project

**High-level flow:**
1. APIs → Cloud Run ingestion scripts  
2. Raw JSON → GCS + BigQuery landing tables  
3. BigQuery transformations → staging → core → marts  
4. BI consumption via Looker / downstream tools  

---

## 2. GCP Project Structure

Separate projects per environment for isolation and clarity:

| Environment | Project ID | Purpose |
|------------|------------|--------|
| **Dev** | `tfl-data-pipeline-dev` | Active development |
| **Staging** | `tfl-data-pipeline-stg` | Validation / QA |
| **Prod** | `tfl-data-pipeline` (display name `tfl-data-pipeline-prod`) | Production workloads |

Ingestion runs once, in prod. Its GCS bucket and `landing` dataset are the single raw source; dev and staging build their own `staging`/`core`/`marts` by reading prod's `landing` cross-project. SQL in this repo targets `-stg`.

---

## 3. Orchestration (Cloud Run)

The pipeline uses **Cloud Run**.

- Python ingestion services deployed to Cloud Run
- Triggered via:
  - Cloud Scheduler (cron-based)
  - Manual HTTP triggers (for testing/backfills)

**Responsibilities:**
- Fetch API data (TFL + Weather)
- Apply light normalization (e.g. flattening, cleaning keys)
- Write to GCS + BigQuery landing tables

---

## 4. GCS Buckets

Environment-specific raw data storage.

**Structure:**

```

gs://tfl-data-pipeline-<env>-raw/
├── tfl_disruptions/YYYY/MM/DD/
└── weather/YYYY/MM/DD/

```


**Examples:**
- `gs://tfl-data-pipeline-dev-raw/tfl_disruptions/2026/04/28/...json`
- `gs://tfl-data-pipeline-dev-raw/weather/2026/04/28/...ndjson`

**Notes:**
- Files are append-only (immutable)
- Used for replay/backfill capability
- NDJSON used where flattening is required (e.g. weather hourly data)

---

## 5. BigQuery Datasets & Layers

A layered ELT architecture aligned to analytics engineering best practice:

| Dataset | Purpose |
|--------|--------|
| `landing` | Raw ingested data (minimal transformation) |
| `staging` | Cleaned, typed, deduplicated |
| `core` | Business logic + conformed models |
| `marts` | Aggregations for BI |

---

### Example Table Flow

**Landing** (prod project only)
- `landing.tfl-disruptions-raw`
- `landing.weather-raw`

**Staging**
- `staging.stg_tfl__disruptions` — current state, one row per `disruption_key`, upserted via MERGE
- `staging.stg_tfl__disruptions__history` — one row per `(disruption_key, last_update)`; append-only change log
- `staging.stg_weather__hourly` — one row per hour, observations preferred over forecasts
- Reject handling for bad records *(planned)*

**Core**
- `core.core_tfl__disruptions__weather` — disruptions joined to observed weather on created hour

**Marts**
- Aggregated metrics for reporting *(planned)*

---

## 6. Table Design Conventions

### Partitioning
- Current-state tables partition on **`DATE(created)`** (event time; better for analytical queries than `fetched_at`)
- History table partitions on **`DATE(fetched_at)`** and clusters on `disruption_key`: it is append-only and queried by load window, and a single disruption spans many `fetched_at` days
- Weather partitions on `DATE(weather_hour)`

### Keys
- Stable primary key via SHA256 hash:
  - `created + description + type`

### Metadata Fields
- `fetched_at` → ingestion timestamp  
- `stg_loaded_at` → transformation timestamp  

### Data Quality
- `SAFE_CAST` used extensively; rows with an uncastable `created` are dropped at staging
- Reject tables *(planned)* will store invalid rows with `reject_reason` and `rejected_at`

---

## 7. Repository Structure

```
tfl-analytics-pipeline/
│
├── ingestion/        # one script per source, deployed to Cloud Run
├── sql/
│ ├── staging/
│ ├── core/
│ └── marts/        # planned
├── notebooks/        # exploration / QA only
└── docs/
```


**Notes:**
- SQL is version-controlled (dbt-style structure without dbt)
- Python handles ingestion only
- Transformations live in BigQuery SQL

---

## 8. Naming Conventions

### Tables

```
<project>.<dataset>.<layer>_<source>__<entity>[__<variant>]


**Examples:**

tfl-data-pipeline-stg.staging.stg_tfl__disruptions
tfl-data-pipeline-stg.staging.stg_tfl__disruptions__history
tfl-data-pipeline-stg.core.core_tfl__disruptions__weather

SQL files follow the table name plus an action suffix: `_bootstrap`, `_merge`, `_insert`.


```


---


## 9. Deployment & Workflow

- Cloud Run services deployed per environment
- SQL executed manually or via scheduled jobs (future automation)

**Branching (lightweight):**
- `main` → stable version
- feature branches → development


---

## 10. IAM Overview

Typical service account per environment:


cloud-run@tfl-data-pipeline-<env>.iam.gserviceaccount.com


**Roles:**
- BigQuery Data Editor (env datasets)
- BigQuery Job User
- Storage Object Admin (env bucket)

---

## 11. References

- [Runbook](runbook.md)
- [Data model dictionary](data_model.md)
