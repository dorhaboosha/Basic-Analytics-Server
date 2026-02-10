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
    data = {
        "userid": f"User{random.randint(1, 100)}",
        "eventname": f"Event{random.randint(1, 50)}",
    }
    r = requests.post(URL, json=data, timeout=TIMEOUT_SECONDS)
    return r.status_code, r.text


if __name__ == "__main__":
    responses = Parallel(n_jobs=PARALLEL_JOBS)(
        delayed(make_request)() for _ in range(NUM_REQUESTS)
    )

    ok = sum(1 for s, _ in responses if s == 200)
    print(f"URL: {URL}")
    print(f"OK: {ok}/{NUM_REQUESTS}")
