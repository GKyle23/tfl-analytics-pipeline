"""
Tests for ingestion/http_client.py (retrying GET helper).

time.sleep is patched in every test so nothing really waits; tenacity sleeps
via time.sleep, so the mock also records the backoff / Retry-After values.
"""
import logging
import sys
from pathlib import Path

import pytest
import requests
import responses

# http_client.py lives in ingestion/, which isn't an installed package, so add
# it to sys.path before importing (same trick as the other test files).
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "ingestion"))

import http_client  # noqa: E402

# Fake endpoint. `responses` intercepts requests before they hit the network,
# so nothing real is ever called.
URL = "https://api.example.com/data"
# Same URL with a fake key in the query string, to check the key never leaks.
SECRET_URL = URL + "?app_key=SUPERSECRET"


@pytest.fixture(autouse=True)
def sleep(monkeypatch):
    # autouse=True: applies to every test automatically. Replaces time.sleep
    # with a function that just records the requested delay, so retries run
    # instantly. Tests can take `sleep` as an argument to inspect the delays.
    calls = []
    monkeypatch.setattr("time.sleep", lambda s: calls.append(s))
    return calls


# NOTE: @responses.activate on each test below switches on the fake HTTP layer.
# responses.add(...) registers what the "server" replies. When several replies
# are registered for the same URL, they are served in order, one per request,
# and the last one repeats once the list runs out.
# responses.calls records every request actually made, so len(responses.calls)
# is the number of attempts.


@responses.activate
def test_200_returns_body():
    # Happy path: one request, body returned, no retries.
    responses.add(responses.GET, URL, json={"ok": True}, status=200)
    resp = http_client.get(URL)
    assert resp.json() == {"ok": True}
    assert len(responses.calls) == 1


@responses.activate
def test_two_503s_then_200_succeeds_on_third_attempt(sleep):
    # Two transient failures then success: 3 requests, 2 sleeps in between.
    responses.add(responses.GET, URL, status=503)
    responses.add(responses.GET, URL, status=503)
    responses.add(responses.GET, URL, json={"ok": True}, status=200)
    resp = http_client.get(URL)
    assert resp.json() == {"ok": True}
    assert len(responses.calls) == 3
    assert len(sleep) == 2


@responses.activate
def test_five_503s_raises(sleep):
    # Only one 503 registered, but it repeats for every request, so the server
    # "always fails". Helper should try 5 times, then raise.
    responses.add(responses.GET, URL, status=503)
    with pytest.raises(requests.HTTPError) as exc:
        http_client.get(URL)
    assert exc.value.response.status_code == 503
    assert len(responses.calls) == 5
    assert len(sleep) == 4  # no sleep after the last attempt


@responses.activate
def test_404_raises_immediately_without_retry(sleep):
    # 4xx (other than 429) is our fault, retrying can't help: 1 attempt, no sleep.
    responses.add(responses.GET, URL, status=404)
    with pytest.raises(requests.HTTPError) as exc:
        http_client.get(URL)
    assert exc.value.response.status_code == 404
    assert len(responses.calls) == 1
    assert sleep == []


@responses.activate
def test_429_honours_retry_after(sleep):
    # Server says "Retry-After: 2": we must wait exactly 2s (not a random
    # backoff). sleep == [2] checks the single recorded delay.
    responses.add(responses.GET, URL, status=429, headers={"Retry-After": "2"})
    responses.add(responses.GET, URL, json={"ok": True}, status=200)
    resp = http_client.get(URL)
    assert resp.status_code == 200
    assert len(responses.calls) == 2
    assert sleep == [2]


@responses.activate
def test_429_without_retry_after_falls_back_to_backoff(sleep):
    # No header: still retried, using normal jittered backoff. The delay is
    # random, so we only assert that one sleep happened.
    responses.add(responses.GET, URL, status=429)
    responses.add(responses.GET, URL, json={}, status=200)
    http_client.get(URL)
    assert len(sleep) == 1


@responses.activate
def test_retry_after_is_capped(sleep):
    # A huge Retry-After (24h) is clamped to MAX_RETRY_AFTER_SECONDS so a bad
    # header can't stall the job.
    responses.add(responses.GET, URL, status=429, headers={"Retry-After": "86400"})
    responses.add(responses.GET, URL, json={}, status=200)
    http_client.get(URL)
    assert sleep == [http_client.MAX_RETRY_AFTER_SECONDS]


@responses.activate
def test_timeout_is_retried(sleep):
    # Passing an exception instance as `body` makes `responses` raise it
    # instead of replying, simulating a request that timed out.
    responses.add(responses.GET, URL, body=requests.Timeout("slow"))
    responses.add(responses.GET, URL, json={"ok": True}, status=200)
    resp = http_client.get(URL)
    assert resp.json() == {"ok": True}
    assert len(responses.calls) == 2
    assert len(sleep) == 1


@responses.activate
def test_connection_error_is_retried_then_raises(sleep):
    # Network down on every attempt: 5 tries, then the ConnectionError surfaces.
    responses.add(responses.GET, URL, body=requests.ConnectionError("down"))
    with pytest.raises(requests.ConnectionError):
        http_client.get(URL)
    assert len(responses.calls) == 5


def test_session_has_10_second_default_timeout():
    # `responses` can't show us the timeout, so we swap Session.send (the
    # lowest layer, where timeout arrives) for a fake that records its kwargs.
    session = http_client.TimeoutSession()
    seen = {}

    def fake_send(self, request, **kwargs):
        seen.update(kwargs)
        raise requests.Timeout("stop here")  # abort; we only wanted the kwargs

    # MonkeyPatch.context() undoes the patch when the block exits.
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(requests.Session, "send", fake_send)
        with pytest.raises(requests.Timeout):
            session.get(URL)
    # We never passed timeout= to session.get(); the default must have been added.
    assert seen["timeout"] == 10


@responses.activate
def test_retries_log_warning_and_final_failure_logs_error_without_app_key(caplog):
    # caplog is pytest's built-in log capture. 5 attempts = 4 retries, each
    # logging a WARNING, then 1 ERROR for the final failure.
    responses.add(responses.GET, URL, status=503)
    with caplog.at_level(logging.WARNING, logger="http_client"):
        with pytest.raises(requests.HTTPError) as exc:
            http_client.get(SECRET_URL)

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(warnings) == 4  # one per retry (none after the last attempt)
    assert "attempt 1/5" in warnings[0].getMessage()
    assert "status=503" in warnings[0].getMessage()
    assert len(errors) == 1
    assert URL in errors[0].getMessage()  # URL is logged, minus the query string

    # The key was in SECRET_URL's query string; it must appear nowhere, neither
    # in the logs nor in the exception the caller receives.
    assert "SUPERSECRET" not in caplog.text
    assert "SUPERSECRET" not in str(exc.value)


@responses.activate
def test_404_error_message_does_not_leak_app_key(caplog):
    # Same leak check on the non-retried path, with the key passed via params
    # (as the real TfL code does). Plain raise_for_status() would include it.
    responses.add(responses.GET, URL, status=404)
    with pytest.raises(requests.HTTPError) as exc:
        http_client.get(URL, params={"app_key": "SUPERSECRET"})
    assert "SUPERSECRET" not in str(exc.value)
    assert "SUPERSECRET" not in caplog.text
