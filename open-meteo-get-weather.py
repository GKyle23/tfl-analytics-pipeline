import os
import json
import datetime as dt
import requests
from google.cloud import storage

BUCKET_NAME= os.getenv("WEATHER_BUCKET_NAME")

    
def fetch_weather_data():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 51.5072,
        "longitude": -0.1276,
        "hourly": ["temperature_2m", "precipitation", "wind_speed_10m", "relative_humidity_2m"],
        "past_days": 1,
        "forecast_days": 1,
        "timezone": "UTC"
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    print("Status:", resp.status_code)
    data = resp.json()
    return data



def upload_to_gcs(data):
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    timestamp = dt.datetime.now(tz=dt.timezone.utc).strftime("%Y/%m/%d/%H")
    blob_name = f"weather_forecast_data/{timestamp}/weather_data.json"
    blob = bucket.blob(blob_name)

    ndjson_string = "\n".join(json.dumps(r) for r in data)

    blob.upload_from_string(
        ndjson_string,
        content_type="application/x-ndjson"
)


def main(request=None):
    raw_data = fetch_weather_data()
    upload_to_gcs(raw_data)
    return 'Weather data uploaded'

if __name__ == "__main__":
    main()
