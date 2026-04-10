"""
Load test for POST /events — sends many concurrent requests and reports success count.

Usage:
  python scripts/load_test.py

Override target (e.g. staging):
  BASE_URL=https://staging.example.com python scripts/load_test.py

Requires: requests, joblib. Install from project root:
  pip install -r requirements.txt

Notes:
- This is a lightweight smoke/load test (not a full benchmark).
- It does not assert response content; it mainly checks the server stays responsive.
- Make sure the API server is running before you execute this script.
"""

import os
import random

import requests
from joblib import Parallel, delayed

# Default is local run:
#   http://127.0.0.1:8000/events
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
URL = f"{BASE_URL.rstrip('/')}/events"

# Tuning knobs:
# - NUM_REQUESTS: total number of requests to send
# - PARALLEL_JOBS: how many concurrent workers to use
# - TIMEOUT_SECONDS: per-request timeout for the HTTP call
NUM_REQUESTS = 25
PARALLEL_JOBS = 10
TIMEOUT_SECONDS = 10


def make_request():
    """POST one random event (user_id, event_name) to /events; returns (status_code, response_text)."""
    # Randomize payloads so you exercise different user/event combinations.
    data = {
        "user_id": f"User{random.randint(1, 100)}",
        "event_name": f"Event{random.randint(1, 50)}",
    }
    # A timeout prevents a single hung request from blocking overall completion.
    r = requests.post(URL, json=data, timeout=TIMEOUT_SECONDS)
    return r.status_code, r.text


if __name__ == "__main__":
    # Run NUM_REQUESTS in parallel (up to PARALLEL_JOBS at a time).
    responses = Parallel(n_jobs=PARALLEL_JOBS)(
        delayed(make_request)() for _ in range(NUM_REQUESTS)
    )

    # Summarize results.
    ok = sum(1 for s, _ in responses if s == 200)
    print(f"URL: {URL}")
    print(f"OK: {ok}/{NUM_REQUESTS}")
