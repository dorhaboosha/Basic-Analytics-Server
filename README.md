# Basic Analytics Server (FastAPI + SQLite)

A small analytics/log server built with **FastAPI** that stores user events in **SQLite** and provides simple reports + visualization.
This project was implemented as part of **Assignment – basic server**.

## Features

- Log events via `POST /process_event`
- Store events in SQLite with a **UTC timestamp**
- Fetch per-user reports from the **last X seconds** via `POST /get_reports`
- View a chart (events per user) via `GET /analyze_events`
- Trigger an outbound phone call via `POST /call_user` (Bland.ai)
- Includes unit tests (`pytest`) and a load test script (`scripts/load_test.py`)

> `call_user` requires a valid **BLAND_API_KEY** and an **E.164** phone number format. Check Bland.ai for supported regions.

---

## API Endpoints

Base URL when running locally: `http://localhost:8000`

### 1) `POST /process_event`
**Request body (JSON):**
```json
{
  "userid": "dudu",
  "eventname": "level2completed"
}
```

**Example**
```bash
curl -X POST "http://localhost:8000/process_event"   -H "Content-Type: application/json"   -d '{"userid":"dudu","eventname":"level2completed"}'
```

---

### 2) `POST /get_reports`
This project implements `get_reports` using **query params**:

`POST /get_reports?lastseconds=<int>&userid=<string>`

**Example**
```bash
curl -X POST "http://localhost:8000/get_reports?lastseconds=200&userid=dudu"
```

---

### 3) `GET /analyze_events`
Returns an **HTML page** with a **PNG chart** (base64-embedded) showing **number of events per user**.

**Example**
Open in browser:
- `http://localhost:8000/analyze_events`

---

### 4) `POST /call_user`
Triggers an automated phone call using **Bland.ai**.

**Request body (JSON):**
```json
{
  "phone_number": "+972501234567"
}
```

**Example**
```bash
curl -X POST "http://localhost:8000/call_user"   -H "Content-Type: application/json"   -d '{"phone_number":"+972501234567"}'
```

---

## Environment Variables

Create a `.env` file (not committed) or export variables in your shell.

**Required**
- `EVENTS_DB_PATH` – path to the sqlite file (example: `./events.db`)
- `BLAND_API_KEY` – required for `POST /call_user`

**Optional**
- `PORT` – server port (default `8000`)

Example `.env`:
```env
EVENTS_DB_PATH=./events.db
BLAND_API_KEY=YOUR_KEY_HERE
PORT=8000
```

---

## Run locally (clone & run)

### 1) Prerequisites
- Python **3.10+**
- pip

### 2) Clone
```bash
git clone https://github.com/dorhaboosha/Basic-Analytics-Server.git
cd Basic-Analytics-Server
```

### 3) Create a virtual environment (recommended)
```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

### 4) Install dependencies
```bash
pip install -r requirements.txt
```

### 5) Run the server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open:
- Swagger UI: `http://localhost:8000/docs`
- Analysis chart: `http://localhost:8000/analyze_events`

---

## Run tests
```bash
pytest -q
```

---

## Run with Docker (build locally)

### Build
```bash
docker build -t basic-analytics-server:latest .
```

### Run
```bash
docker run --rm -p 8000:8000   -e EVENTS_DB_PATH=/data/events.db   -e BLAND_API_KEY="YOUR_KEY_HERE"   -v "$(pwd)/data:/data"   basic-analytics-server:latest
```

---

## Download & run (ZIP)

If you download this repository as a ZIP (instead of cloning), you can still run it easily:

1. Download ZIP → extract
2. Open a terminal inside the extracted folder
3. Build + run with Docker:
```bash
docker build -t basic-analytics-server:latest .
docker run --rm -p 8000:8000   -e EVENTS_DB_PATH=/data/events.db   -e BLAND_API_KEY="YOUR_KEY_HERE"   -v "$(pwd)/data:/data"   basic-analytics-server:latest
```

---

## Load test

This repository includes: `scripts/load_test.py`  
It sends multiple `POST /process_event` requests in parallel using **joblib**.

### Run against local server
1) Start the server (local or Docker)  
2) Run:
```bash
python scripts/load_test.py
```

### Run against a different host
Set `BASE_URL` (the script appends `/process_event` automatically):
```bash
# Windows (PowerShell):
$env:BASE_URL="http://127.0.0.1:8000"; python scripts/load_test.py

# macOS/Linux:
BASE_URL="http://127.0.0.1:8000" python scripts/load_test.py
```

---

## Project structure

```
.
├─ main.py
├─ Dockerfile
├─ requirements.txt
├─ scripts/
│  └─ load_test.py
└─ tests/
```

---

## License
This project is provided for learning purposes.
