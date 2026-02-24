import os
import json
import datetime as dt
import requests
from google.cloud import storage

APP_KEY= os.getenv("TFL_APP_KEY")
BUCKET_NAME= os.getenv("TFL_BUCKET_NAME")
MODES = "tube,dlr,overground,elizabeth-line,tram,bus"

def fetch_tfl_data():
    url = f"https://api.tfl.gov.uk/Line/Mode/{MODES}/Disruption"
    params = {"app_key": APP_KEY}
    headers = {"Cache-Control": "no-cache"}
    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()
    return resp.json()   # returns a list of disruptions


def clean_record(record):
    cleaned = {}
    cleaned["fetched_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    for key, value in record.items():
        if key.startswith("$"):
            clean_key = key.replace("$", "meta_")   # e.g. $type → meta_type
        else:
            clean_key = key
        cleaned[clean_key] = value
    return cleaned


def clean_data(records):
    return [clean_record(r) for r in records]


def upload_to_gcs(cleaned_records):
    print(">>> ENTERED UPLOAD", flush=True)
    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)

        timestamp = dt.datetime.now().strftime("%Y/%m/%d/%H")
        blob_name = f"tfl_disruptions/{timestamp}/tfl_disruptions.json"
        blob = bucket.blob(blob_name)

        ndjson_string = "\n".join(json.dumps(r) for r in cleaned_records)

        blob.upload_from_string(
            ndjson_string,
            content_type="application/x-ndjson"
        )

        print(f"Uploaded to gs://{BUCKET_NAME}/{blob_name}", flush=True)

    except Exception as e:
        print("UPLOAD FAILED:", repr(e), flush=True)
        raise


def main(request=None):
    raw_data = fetch_tfl_data()
    cleaned = clean_data(raw_data)
    upload_to_gcs(cleaned)
    return "TFL Disruptions data fetched, cleaned, and uploaded to GCS."


if __name__ == "__main__":
    main()




