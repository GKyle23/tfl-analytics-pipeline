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


# Enforced schema
def clean_record(record, now_iso):
    return {
        "meta_type": record.get("$type"),

        "category": record.get("category"),
        "type": record.get("type"),
        "description": record.get("description"),
        "categoryDescription": record.get("categoryDescription"),

        # ALWAYS present 
        "created": record.get("created"),
        "lastUpdate": record.get("lastUpdate"),

        "closureText": record.get("closureText"),

        # Arrays always present
        "affectedRoutes": record.get("affectedRoutes", []),
        "affectedStops": record.get("affectedStops", []),

        # Optional field (safe)
        "additionalInfo": record.get("additionalInfo"),

        # Ingestion timestamp
        "fetched_at": now_iso
    }


def clean_data(records):
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
    cleaned = []

    for r in records:
        try:
            row = clean_record(r, now_iso)

            # Ensure JSON serialisable 
            json.dumps(row)

            cleaned.append(row)

        except Exception as e:
            print("Skipping bad record:", repr(e), flush=True)

    return cleaned


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




