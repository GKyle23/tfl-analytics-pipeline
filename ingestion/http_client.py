"""
Shared HTTP helper for the ingestion scripts.

A requests.Session with a default timeout, wrapped in a tenacity retry:
  * up to 5 attempts, exponential backoff with full jitter
  * retries connection errors, timeouts, 429 and 5xx
  * gives up immediately on any other 4xx
  * honours Retry-After on a 429 (seconds or HTTP-date)
  * each retry is logged at WARNING, the final failure at ERROR

Logged URLs and exception messages never include the query string, because the
TfL app_key travels there.

(Named http_client rather than http: ingestion/ is put on sys.path directly,
so a module called http would shadow the stdlib http package and break
requests/urllib3.)
"""
import logging
import re
from email.utils import parsedate_to_datetime
import datetime as dt
from urllib.parse import urlsplit, urlunsplit

import requests
from tenacity import (
    RetryCallState,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10
MAX_ATTEMPTS = 5
MAX_RETRY_AFTER_SECONDS = 60  # don't let a server park us for longer than this

# Backoff with jitter: waits a random time between 0 and 1s, 2s, 4s, 8s...
# (doubling each attempt), never more than 30s. The randomness stops many
# callers retrying in lockstep after an outage.
_backoff = wait_random_exponential(multiplier=1, max=30)

# Matches "app_key=<value>" in any text so we can mask the value.
_SECRET_RE = re.compile(r"(app_key=)[^&\s'\")]*", re.IGNORECASE)


class RetryableHTTPError(requests.HTTPError):
    """429 / 5xx response: worth another attempt.

    Raising this (rather than a plain HTTPError) is how _send tells tenacity
    "retry me". retry_after carries the server's requested delay, if any.
    """

    def __init__(self, message, response, retry_after=None):
        super().__init__(message, response=response)
        self.retry_after = retry_after


class TimeoutSession(requests.Session):
    """Session that applies a default timeout to every request.

    requests.Session has no built-in default timeout (without one a hung
    server blocks forever), so we inject one on every call.
    """

    def __init__(self, timeout=TIMEOUT_SECONDS):
        super().__init__()
        self.timeout = timeout

    def request(self, method, url, *args, **kwargs):
        # setdefault: a caller passing its own timeout still wins.
        kwargs.setdefault("timeout", self.timeout)
        return super().request(method, url, *args, **kwargs)


def _safe_url(url):
    """URL with query string and fragment dropped."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _redact(text):
    return _SECRET_RE.sub(r"\1***", str(text))


def _parse_retry_after(value):
    """Retry-After is either a number of seconds ("2") or an HTTP date.

    Returns seconds to wait (clamped to 0..MAX_RETRY_AFTER_SECONDS), or None
    if the header is missing or unparseable.
    """
    if not value:
        return None
    value = value.strip()
    try:
        seconds = float(value)  # form 1: "Retry-After: 2"
    except ValueError:
        try:  # form 2: "Retry-After: Wed, 21 Oct 2026 07:28:00 GMT"
            when = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=dt.timezone.utc)
        seconds = (when - dt.datetime.now(dt.timezone.utc)).total_seconds()
    return min(max(seconds, 0), MAX_RETRY_AFTER_SECONDS)


def _wait(retry_state: RetryCallState):
    """Tenacity wait strategy: obey Retry-After if the server sent one,
    otherwise use the jittered exponential backoff."""
    outcome = retry_state.outcome
    exc = outcome.exception() if outcome else None
    retry_after = getattr(exc, "retry_after", None)
    if retry_after is not None:
        return retry_after
    return _backoff(retry_state)


def _describe(exc):
    """Short label for logs: the HTTP status, or the exception class name."""
    status = getattr(getattr(exc, "response", None), "status_code", None)
    return f"status={status}" if status is not None else f"error={type(exc).__name__}"


def _log_retry(retry_state: RetryCallState):
    """Runs after a failed attempt, just before tenacity sleeps: WARNING log."""
    url = retry_state.kwargs["safe_url"]
    outcome = retry_state.outcome
    exc = outcome.exception() if outcome else None
    logger.warning(
        "Retrying %s (attempt %d/%d failed, %s)",
        url, retry_state.attempt_number, MAX_ATTEMPTS, _describe(exc),
    )


def _send(session, url, safe_url, **kwargs):
    """One attempt. Classifies the response so tenacity knows whether to retry:
    429/5xx -> RetryableHTTPError (retry), other 4xx -> HTTPError (give up),
    anything else -> return the response. Connection errors and timeouts
    propagate from session.get() as-is and are retried by the policy below.
    """
    resp = session.get(url, **kwargs)
    status = resp.status_code
    if status == 429 or status >= 500:
        raise RetryableHTTPError(
            f"{status} {resp.reason} for url: {safe_url}",
            response=resp,
            retry_after=_parse_retry_after(resp.headers.get("Retry-After"))
            if status == 429 else None,
        )
    if status >= 400:
        # Not retryable. Built by hand: raise_for_status() puts the full URL,
        # query string included, in the message.
        raise requests.HTTPError(
            f"{status} {resp.reason} for url: {safe_url}", response=resp
        )
    return resp


def get(url, params=None, headers=None, session=None):
    """GET with retries. Returns the Response, raises on final failure."""
    session = session or TimeoutSession()
    safe_url = _safe_url(url)  # computed once; only this form is ever logged
    retrying = Retrying(
        stop=stop_after_attempt(MAX_ATTEMPTS),  # 5 tries total, not 5 retries
        wait=_wait,
        # Retry only these exception types; anything else (e.g. a 404's
        # HTTPError) propagates immediately.
        retry=retry_if_exception_type(
            (RetryableHTTPError, requests.ConnectionError, requests.Timeout)
        ),
        before_sleep=_log_retry,
        reraise=True,  # surface the real last error, not tenacity's RetryError
    )
    try:
        return retrying(
            _send, session, url, safe_url=safe_url, params=params, headers=headers
        )
    except requests.RequestException as exc:
        # Reached on a non-retryable error or after the last attempt failed.
        logger.error("Giving up on %s (%s): %s", safe_url, _describe(exc), _redact(exc))
        # Mask the key in the exception we re-raise too, since callers or the
        # runtime may log it.
        exc.args = tuple(_redact(a) for a in exc.args)
        raise
