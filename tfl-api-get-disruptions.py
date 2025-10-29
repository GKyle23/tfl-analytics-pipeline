import os
import json
import datetime as dt
import requests
from google.cloud import storage

APP_KEY= os.getenv("TFL_APP_KEY")
BUCKET_NAME= os.getenv("BUCKET_NAME")
MODES = "tube,dlr,overground,elizabeth-line,tram,bus"

def fetch_tfl_data():
    url = f"https://api.tfl.gov.uk/Line/Mode/{MODES}/Disruption"
    params = {"app_key": APP_KEY}
    headers = {"Cache-Control": "no-cache"}
    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status() # raises Python exception if response is not 2xx status
    print("Status:", resp.status_code)
    data = resp.json()
    print(resp.json())
    return data
    

def upload_to_gcs(data):
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    timestamp = dt.datetime.now().strftime("%Y/%m/%d/%H")
    blob_name = f"tfl_disruptions/{timestamp}/tfl_disruptions.json"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(
        json.dumps(data, indent=2),
        content_type="application/json"
    )


def main():
    raw_data = fetch_tfl_data()
    upload_to_gcs(raw_data)

if __name__ == "__main__":
    main()


