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
        # Fetch hourly data for the past day and next day
        "hourly": ["temperature_2m", "precipitation", "wind_speed_10m", "relative_humidity_2m"],
        "past_days": 1,
        "forecast_days": 1,
        "timezone": "UTC"
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    print("Status:", resp.status_code)
    data = resp.json()
    print(data)
    return data



fetch_weather_data()


"""

def upload_to_gcs(data):
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    timestamp = dt.datetime.now().strftime("%Y/%m/%d/%H")
    blob_name = f"tfl_disruptions/{timestamp}/weather_data.json"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(
        json.dumps(data, indent=2),
        content_type="application/json"
    )


def main():
    raw_data = fetch_weather_data()
    upload_to_gcs(raw_data)

if __name__ == "__main__":
    main()

    """