# TFL Analytics Pipeline
An example pipeline that enriches TFL data with weather data fo analytics readinesss in Big Query.

## Architecture
The pipeline uses the following GCP components:
- **Cloud Composer (Airflow)** - Orhestrates pipeline DAGS
- **Cloud Storage** - Stores the raw JSON API data
- **Big Query** - Stores raw,enriched and summarty datasets
- **Looker** - Visusalising trends and comparisons.

Data flow:
TFL API & Weather API → GCS (raw JSON) → BigQuery (raw) → BigQuery (staging/enriched) → BigQuery (summary) → Looker

## Features
- Hourly ingestion of TFL disruption data
- Weather enrichment via external API
- Raw JSON archiving in GCS
- Partitioned and clustered BigQuery tables for performance and cost control
- Airflow DAG orchestration with retries and alerting
- Layered data modeling (raw → staging → enriched → summary)
- Looker dashboard for trends


## Repository Structure
```/dags/                  # Airflow DAG definitions
/sql/                   # SQL transformation scripts for BigQuery
/docs/                  # Documentation (scaffold, data dictionary, runbook)
/infra/                 # Infrastructure scripts/config
requirements.txt        # Python dependencies for DAGs
README.md               # This file
```


## Environments
The pipeline runs in **development**, **staging**, and **production** environments in GCP.  

Each environment has:
- Dedicated Composer environment
- Separate GCS bucket for raw data
- Separate BigQuery datasets

DAG deployment is branch-based:
- **`dev` branch** → Dev Composer environment
- **`staging` branch** → Staging Composer environment
- **`main` branch** → Production Composer environment

Cloud Build syncs the `/dags` folder to the appropriate Composer bucket based on branch.


## Documentation Links
- [Scaffold & Environment Setup](docs/scaffold.md)
- [Data Model Dictionary](docs/data_model.md)
- [Runbook](docs/runbook.md)
