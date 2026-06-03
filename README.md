# TFL Analytics Pipeline 🚧 *(Work in Progress)*

An end-to-end data pipeline that ingests Transport for London (TfL) disruption data and weather data, stores raw API responses in Google Cloud Storage, and prepares analytics-ready datasets in BigQuery.

> ⚠️ **Status:** This project is actively being developed.
> Expect incomplete features, evolving data models, and ongoing refactoring.

---

## Overview

This project demonstrates a modern analytics engineering workflow on Google Cloud Platform (GCP), including:

- API ingestion using Python
- Raw data archiving in Cloud Storage
- Incremental data processing in BigQuery
- Layered data modeling
- Analytics-ready outputs for reporting and exploration

**Project Goal**

Explore the relationship between transport disruptions and weather conditions by combining TfL disruption data with weather observations and forecasts.

---

## Architecture

The pipeline uses the following GCP components:

- **Cloud Run** – Executes ingestion services
- **Cloud Scheduler** – Triggers ingestion jobs
- **Cloud Storage (GCS)** – Stores raw JSON API responses
- **BigQuery** – Stores staging, historical, and analytics datasets
- **Looker** *(planned)* – Visualisation and reporting

### Data Flow

```text
TFL API + Weather API
          ↓
Cloud Run
          ↓
Cloud Storage (raw JSON archive)
          ↓
BigQuery Landing
          ↓
BigQuery Staging
          ↓
BigQuery Historical Models
          ↓
Analytics & Reporting


---

## Features

### Data Ingestion

- TfL disruption API ingestion
- Open-Meteo weather API ingestion
- Raw JSON archival in GCS
- Timestamped data collection

### Data Processing

- Bootstrap scripts for table creation
- Incremental MERGE processing
- Historical disruption tracking
- Data validation and type casting
- Idempotent loading patterns

### Analytics Engineering Practices

- Layered data architecture
- Partitioned BigQuery tables
- Incremental processing
- Separation of raw and historical datasets
- Documentation and runbooks

---

## Repository Structure


```
docs/
├── data_model.md
├── runbook.md
└── scaffold.md

ingestion/
├── open-meteo-get-weather.py
├── tfl-api-explorer.py
└── tfl-api-get-disruptions.py

sql/
└── staging/
    └── tfl/
        ├── stg_tfl_disruptions_bootstrap.sql
        ├── stg_tfl_disruptions_raw_bootstrap.sql
        ├── stg_tfl_disruptions_raw_merge.sql
        ├── stg_tfl_disruptions_history_bootstrap.sql
        └── stg_tfl_disruptions_history_insert.sql

README.md
requirements.txt
runtime.txt
```


---

## Environments

The pipeline is deployed across **dev**, **staging**, and **production** environments.


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