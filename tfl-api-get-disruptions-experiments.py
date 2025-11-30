import os
import json
import datetime as dt
import requests
from google.cloud import storage

APP_KEY= os.getenv("TFL_APP_KEY")
BUCKET_NAME= os.getenv("BUCKET_NAME")
MODES = "tube,dlr,overground,elizabeth-line,tram,bus"
SERVICE_ACCOUNT_JSON= os.getenv("SERVICE_ACCOUNT_JSON")

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
    


def authenticate_gcs(service_account_json: str = None):
    if service_account_json:
        return storage.Client.from_service_account_json(service_account_json)



def upload_to_gcs(data,client):
    bucket = client.bucket(BUCKET_NAME)
    timestamp = dt.datetime.now().strftime("%Y/%m/%d/%H")
    blob_name = f"tfl_disruptions/{timestamp}/tfl_disruptions.json"
    blob = bucket.blob(blob_name)
    # upload as ndjson
    blob.upload_from_string(
        "\n".join(json.dumps(record) for record in data), # use generator expression to save memory
        content_type="application/x-ndjson"
    )
    print(f"uploaded to gs bucket {BUCKET_NAME}/{blob_name}")

def main():
    client = authenticate_gcs(SERVICE_ACCOUNT_JSON)
    raw_data = fetch_tfl_data()
    upload_to_gcs(raw_data,client)

if __name__ == "__main__":
    main()


