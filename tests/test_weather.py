"""
Unit tests for ingestion/weather.py's flatten_to_ndjson.

tests/fixtures/weather_response.json is a *real* response captured from
https://api.open-meteo.com/v1/forecast (same params as fetch_weather_data:
past_days=1, forecast_days=1, UTC) on 2026-11-02. It's a genuine 48-hour
response -- the mismatched-length edge cases below don't exist in real
Open-Meteo responses, so those are built from a copy with one hourly field
truncated/extended, same approach test_tfl_disruptions.py uses for its own
synthetic edge cases.
"""
import json
import sys
from pathlib import Path

import pytest

# weather.py lives in ingestion/, which isn't a package and isn't installed,
# so we add it to sys.path ourselves before importing it (same trick as
# test_tfl_disruptions.py; see pyrightconfig.json's "extraPaths" for why
# Pylance/Pyright doesn't flag this import as unresolved).
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "ingestion"))

import weather  # noqa: E402

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "weather_response.json"


@pytest.fixture
def real_response():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_flatten_to_ndjson_48_hour_response_gives_48_lines_same_fetched_at(real_response):
    # The fixture itself is a real past_days=1 + forecast_days=1 capture, so
    # this is exercising the actual 48-hour shape, not a stand-in for it.
    assert len(real_response["hourly"]["time"]) == 48

    ndjson = weather.flatten_to_ndjson(real_response)
    lines = ndjson.split("\n")

    assert len(lines) == 48

    # json.loads raises if any line isn't valid JSON, so this doubles as the
    # "each line is valid JSON" check.
    rows = [json.loads(line) for line in lines]

    # fetched_at is computed once per flatten_to_ndjson() call (before the
    # row loop), not once per row, so every row should carry the exact same
    # value. A set collapses duplicates, so len == 1 means "all identical".
    fetched_at_values = {row["fetched_at"] for row in rows}
    assert len(fetched_at_values) == 1


def test_flatten_to_ndjson_shorter_non_time_array_raises_indexerror(real_response):
    # Copy the real response and truncate one hourly field -- a real
    # Open-Meteo response always returns equal-length hourly arrays, so this
    # simulates the API breaking that contract.
    data = dict(real_response)
    data["hourly"] = dict(real_response["hourly"])
    data["hourly"]["temperature_2m"] = real_response["hourly"]["temperature_2m"][:3]

    # flatten_to_ndjson iterates over "time" and indexes every other hourly
    # field with the same i, with no bounds checking and no per-row
    # try/except (unlike tfl_disruptions.clean_data, which catches and skips
    # bad records individually). So a short array doesn't drop just that
    # hour -- it blows up the whole call.
    with pytest.raises(IndexError):
        weather.flatten_to_ndjson(data)


def test_flatten_to_ndjson_longer_non_time_array_silently_drops_extra_values(real_response):
    # The opposite direction of the mismatch: an hourly field with MORE
    # entries than "time". Since the loop is driven by enumerate(time), this
    # doesn't raise -- the extra values past len(time) are just never read.
    data = dict(real_response)
    data["hourly"] = dict(real_response["hourly"])
    data["hourly"]["temperature_2m"] = real_response["hourly"]["temperature_2m"] + [999.0, 999.0]

    ndjson = weather.flatten_to_ndjson(data)
    rows = [json.loads(line) for line in ndjson.split("\n")]

    # Still only 48 rows (one per "time" entry), and none of them pick up
    # the extra 999.0 sentinel values -- documenting that this mismatch is
    # silently tolerated rather than flagged, unlike the shorter-array case.
    assert len(rows) == len(real_response["hourly"]["time"])
    assert all(row["temperature_2m"] != 999.0 for row in rows)
