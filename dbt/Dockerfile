FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# profiles.yml lives next to dbt_project.yml; auth comes from the Cloud Run
# job's service account (Application Default Credentials).
ENV DBT_PROFILES_DIR=/app

ENTRYPOINT ["dbt"]
CMD ["build", "--target", "cloud"]
