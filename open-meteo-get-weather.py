print(">>> MODULE IMPORTED <<<", flush=True)


import os
import json
import datetime as dt
import requests
import logging
from google.cloud import storage

logging.basicConfig(level=logging.INFO)

BUCKET_NAME = os.getenv("WEATHER_BUCKET_NAME")


def fetch_weather_data():
    logging.info("Fetching weather data")
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 51.5072,
        "longitude": -0.1276,
        "hourly": [
            "temperature_2m",
            "precipitation",
            "wind_speed_10m",
            "relative_humidity_2m"
        ],
        "past_days": 1,
        "forecast_days": 1,
        "timezone": "UTC"
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    logging.info("Weather API status %s", resp.status_code)
    return resp.json()


def flatten_to_ndjson(data):
    hourly = data["hourly"]

    rows = []
    for i, ts in enumerate(hourly["time"]):
        rows.append({
            "time": ts,
            "temperature_2m": hourly["temperature_2m"][i],
            "precipitation": hourly["precipitation"][i],
            "wind_speed_10m": hourly["wind_speed_10m"][i],
            "relative_humidity_2m": hourly["relative_humidity_2m"][i],
            "latitude": data["latitude"],
            "longitude": data["longitude"]
        })

    return "\n".join(json.dumps(r) for r in rows)


def upload_to_gcs(ndjson_string):
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)

    timestamp = dt.datetime.now(tz=dt.timezone.utc).strftime("%Y/%m/%d/%H")
    blob_name = f"weather_forecast_data/{timestamp}/weather_data.ndjson"

    logging.info("Uploading to gs://%s/%s", BUCKET_NAME, blob_name)

    blob = bucket.blob(blob_name)
    blob.upload_from_string(
        ndjson_string,
        content_type="application/x-ndjson"
    )


def main(request=None):
    print(">>> MAIN STARTED <<<", flush=True)
    raw_data = fetch_weather_data()
    ndjson = flatten_to_ndjson(raw_data)
    upload_to_gcs(ndjson)
    print(">>> MAIN FINISHED <<<", flush=True)
    return "Weather data fetched, cleaned, and uploaded to GCS."

if __name__ == "__main__":
    main()
