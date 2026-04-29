
# TFL Analytics Pipeline 🚧 *(Work in Progress)*

An end-to-end data pipeline that ingests Transport for London (TfL) disruption data, enriches it with weather data, and models it for analytics use in BigQuery.

> ⚠️ **Status:** This project is actively being developed.  
> Expect incomplete features, evolving data models, and ongoing refactoring.

---

## Overview

This project demonstrates a modern analytics engineering workflow on Google Cloud Platform (GCP), including ingestion, transformation, enrichment, and modeling.

**Core idea:**  
Combine transport disruption data with weather conditions to enable richer analytical insights (e.g. correlation between weather and service disruptions).

---

## Architecture

The pipeline uses the following GCP components:
- **Cloud Run** – Executes ingestion services (containerised, serverless)
- **Cloud Scheduler** – Triggers ingestion jobs on a schedule
- **Cloud Storage** - Stores the raw JSON API data
- **Big Query** - Stores raw,enriched and summary datasets
- **Looker** - Visusalising trends and comparisons.

### Data Flow

TFL API + Weather API
↓
GCS (raw JSON)
↓
BigQuery (landing/raw)
↓
BigQuery (staging / enriched)
↓
BigQuery (analytics / marts)
↓
Looker dashboards


---

## Features

- Hourly ingestion of TfL disruption data  
- Weather enrichment via external API  
- Raw JSON archiving in GCS (data lake pattern)  
- Partitioned BigQuery tables for performance and cost efficiency  
- Incremental processing using merge strategies (idempotent loads)  
- Airflow DAG orchestration with retry logic  
- Layered data modeling:
  - **Landing → Staging → Core → Marts**
- Initial Looker dashboard for trend exploration  

---

## Repository Structure


```
/ingestion/ # Cloud Run ingestion services

/sql/ # BigQuery transformation logic
├── staging/ # Cleaning + type casting + deduplication
├── core/ # Business logic models
└── marts/ # Analytics-ready tables

/docs/ # Documentation (data model, runbook, setup)
/infra/ # Infrastructure/configuration scripts
requirements.txt
runtime.txt
README.md
```


---

## Environments

The pipeline is deployed across **dev**, **staging**, and **production** environments.

Each environment includes:
- Dedicated Composer environment  
- Separate GCS bucket  
- Separate BigQuery datasets  

### Deployment Model

Branch-based deployment:

- `dev` → Development environment  
- `staging` → Staging environment  
- `main` → Production environment  

Cloud Build syncs DAGs to Composer based on branch.

---

## Current Focus (WIP)

- Improving data quality and validation (rejects handling)  
- Refining incremental load strategy (MERGE patterns)  
- Expanding weather enrichment coverage  
- Building out analytics-ready marts  
- Enhancing observability and pipeline monitoring  

---

## Documentation

- [Scaffold & Environment Setup](docs/scaffold.md)  
- [Data Model Dictionary](docs/data_model.md)  
- [Runbook](docs/runbook.md)  

---

## Why this project?

This project is designed to reflect **real-world analytics engineering practices**, including:

- Handling semi-structured API data  
- Designing idempotent pipelines  
- Building layered data models  
- Working across multiple environments  
- Balancing cost, performance, and data quality in BigQuery  