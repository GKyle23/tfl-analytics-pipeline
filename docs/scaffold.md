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
| **Prod** | `tfl-data-pipeline-prod` | Production workloads |

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

**Landing**
- `landing.tfl_disruptions_raw`
- `landing.weather_raw`

**Staging**
- `staging.tfl_disruptions_stg`
- Deduplication via hashed `disruption_key`
- Reject handling for bad records

**Core**
- Joined/enriched datasets (TFL + weather)

**Marts**
- Aggregated metrics for reporting

---

## 6. Table Design Conventions

### Partitioning
- Partition on **`DATE(created)`**
- Chosen over ingestion time (`fetched_at`) because:
  - Aligns with event time
  - Better for analytical queries

### Keys
- Stable primary key via SHA256 hash:
  - `created + description + type`

### Metadata Fields
- `fetched_at` → ingestion timestamp  
- `stg_loaded_at` → transformation timestamp  

### Data Quality
- `SAFE_CAST` used extensively
- Reject tables store:
  - invalid rows
  - `reject_reason`
  - `rejected_at`

---

## 7. Repository Structure

```
tfl-analytics-pipeline/
│
├── ingestion/
│ ├── tfl/
│ ├── weather/
│ └── utils/
│
├── sql/
│ ├── landing/
│ ├── staging/
│ ├── core/
│ └── marts/
│
├── notebooks/ # exploration / QA only
├── README.md
└── scaffold.md
```


**Notes:**
- SQL is version-controlled (dbt-style structure without dbt)
- Python handles ingestion only
- Transformations live in BigQuery SQL

---

## 8. Naming Conventions

### Tables

```
<project>.<dataset>.<layer>_<entity>__<layer>__<purpose>


**Examples:**

tfl-data-pipeline-stg.staging.stg_tfl__disruptions
tfl-data-pipeline-stg.landing.stg_tfl__disruptions__raw


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

- Runbook *(TBD)*
- Data model dictionary *(TBD)*
