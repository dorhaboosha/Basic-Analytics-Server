###### Our Names and IDs ######
# Moran Herzlinger - 314710500
# Dor Haboosha - 208663534
# Itay Golan - 206480402
#####################

import random
import requests
from joblib import Parallel, delayed

# Endpoint URL
url = "http://20.217.131.146:8000/process_event/"

# Function to make a POST request to the server - random.randint(1, 100)
def make_request():
    # Generate random data
    data = {
        "userid": f"User{random.randint(1, 100)}",
        "eventname": f"Event{random.randint(1, 50)}"
    }

    # Make POST request
    response = requests.post(url, json=data)
    return response.status_code, response.json()

# Number of requests
num_requests = 1000

# Using joblib to run requests in parallel
responses = Parallel(n_jobs=-1)(delayed(make_request)() for _ in range(num_requests))

# Optional: Print responses for verification
for status_code, content in responses:
    print(f"Status Code: {status_code}, Response: {content}")
