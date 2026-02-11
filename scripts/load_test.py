"""
Load test for POST /process_event — sends many concurrent requests and reports success count.

Usage:
  python scripts/load_test.py

  Override target (e.g. staging):
  BASE_URL=https://staging.example.com python scripts/load_test.py

Requires: requests, joblib. Install from project root: pip install -r requirements.txt
"""

import os
import random
import requests
from joblib import Parallel, delayed

# Default is local Docker run:
#   http://127.0.0.1:8000/process_event
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
URL = f"{BASE_URL.rstrip('/')}/process_event"

NUM_REQUESTS = 25
PARALLEL_JOBS = 10
TIMEOUT_SECONDS = 10


def make_request():
    """POST one random event (userid, eventname) to /process_event; returns (status_code, response_text)."""
    data = {
        "userid": f"User{random.randint(1, 100)}",
        "eventname": f"Event{random.randint(1, 50)}",
    }
    r = requests.post(URL, json=data, timeout=TIMEOUT_SECONDS)
    return r.status_code, r.text


if __name__ == "__main__":
    # Run NUM_REQUESTS in parallel (PARALLEL_JOBS at a time) and print OK/total.
    responses = Parallel(n_jobs=PARALLEL_JOBS)(
        delayed(make_request)() for _ in range(NUM_REQUESTS)
    )

    ok = sum(1 for s, _ in responses if s == 200)
    print(f"URL: {URL}")
    print(f"OK: {ok}/{NUM_REQUESTS}")
