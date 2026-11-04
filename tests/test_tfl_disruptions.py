"""
Unit tests for ingestion/tfl_disruptions.py.

tests/fixtures/tfl_disruptions_response.json is a trimmed, *real* response
captured from https://api.tfl.gov.uk/Line/Mode/.../Disruption on 2026-10-30.
It happens to contain:
  - records with lastUpdate present (normal shape)
  - records with lastUpdate (and closureText) entirely absent from the dict

The live API never omits "affectedRoutes" and never returns a value that
json.dumps can't serialise, so those two edge cases are built from synthetic
records (copies of the real shape with one field removed/corrupted) rather
than captured responses.
"""


import json
import sys
from pathlib import Path
import os

import pytest


# tfl_disruptions.py lives in ingestion/, which isn't a package (no __init__.py)
# and isn't installed, so Python won't find it on the normal import path.
# We fix that at runtime by adding ingestion/ to sys.path ourselves, before
# the import below runs. (Pylance/Pyright can't see this trick statically —
# that's what pyrightconfig.json's "extraPaths" is for.)
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "ingestion"))

# noqa: E402 tells linters "yes, I know this import isn't at the top of the
# file — that's intentional, it has to come after the sys.path.insert above."
import tfl_disruptions  # noqa: E402

# Path to the saved sample API response, resolved relative to this test file
# (not the current working directory) so tests work no matter where pytest
# is invoked from.
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "tfl_disruptions_response.json"

# A pytest fixture: a reusable setup function. Any test below that declares
# "real_records" as a parameter gets the return value of this function
# (pytest calls it automatically and passes the result in) — freshly loaded
# from disk for each test, so no test can accidentally mutate data another
# test depends on.
@pytest.fixture
def real_records():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)

def test_clean_record_normal_record_maps_every_field(real_records):
    # Take one real, "normal" disruption record straight from the fixture.
    record = real_records[0]
    fetched_at = "2026-10-30T12:00:00+00:00"

    # Call the function under test directly (no HTTP, no GCS — just the
    # pure transformation logic).
    result = tfl_disruptions.clean_record(record, fetched_at)

    # Check every single output field by hand, so a bug that silently drops
    # or mis-maps one field would be caught immediately.
    assert result == {
        "meta_type": record["$type"],
        "category": record["category"],
        "type": record["type"],
        "description": record["description"],
        "categoryDescription": record["categoryDescription"],
        "created": record["created"],
        "lastUpdate": record["lastUpdate"],
        "closureText": None,  # closureText is a real field in TfL's schema but test response doesn't have it
        "affectedRoutes": record["affectedRoutes"],
        "affectedStops": record["affectedStops"],
        "additionalInfo": None,
        "fetched_at": fetched_at,
    }

def test_clean_record_missing_lastupdate_and_closuretext_gives_none(real_records):
    # real_records[2] is a captured record with no "lastUpdate" key at all,
    # and no record in a TfL response has ever carried "closureText" either.
    record = real_records[2]
    # Sanity-check our assumption about the fixture before relying on it —
    # if the fixture file ever changes, this fails loudly instead of the
    # test silently testing nothing.
    assert "lastUpdate" not in record
    assert "closureText" not in record

    result = tfl_disruptions.clean_record(record, "2026-10-30T12:00:00+00:00")

    # clean_record uses dict.get(key), which returns None for a missing key
    # instead of raising KeyError — this proves that's actually what happens.
    assert result["lastUpdate"] is None
    assert result["closureText"] is None


def test_clean_record_missing_affectedroutes_gives_empty_list(real_records):
    # Copy a real record (dict(...) makes a shallow copy so we don't mutate
    # the fixture) and delete a key the live API always sends, to simulate
    # a shape the API doesn't actually produce but the code should still
    # handle safely.
    record = dict(real_records[0])
    del record["affectedRoutes"]
    assert "affectedRoutes" not in record

    result = tfl_disruptions.clean_record(record, "2026-10-30T12:00:00+00:00")

    # clean_record.get("affectedRoutes", []) should fall back to an empty
    # list, not None and not a KeyError.
    assert result["affectedRoutes"] == []


def test_clean_data_skips_unserialisable_record_keeps_rest(real_records):
    good_records = real_records[:2]
    bad_record = dict(real_records[0])
    # A Python set can't be converted to JSON, so json.dumps(row) will raise
    # a TypeError for this record specifically, inside clean_data's loop.
    bad_record["additionalInfo"] = {"this", "is", "a", "set"}

    # clean_data is expected to catch that per-record error, print/log it,
    # and continue — not let one bad record blow up the whole batch.
    cleaned = tfl_disruptions.clean_data(good_records + [bad_record])

    # Only the 2 good records should survive; the bad one is silently dropped.
    assert len(cleaned) == len(good_records)
    descriptions = {row["description"] for row in cleaned}
    assert descriptions == {r["description"] for r in good_records}






