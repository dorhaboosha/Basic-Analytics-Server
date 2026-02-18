# Basic Analytics Server (FastAPI + SQLite)

A small analytics/log server built with **FastAPI** that stores user events in **SQLite** and provides simple reports + visualization.  
This project was implemented as part of an **Assignment – basic server**.

## Features

- **Record events** into SQLite (UTC timestamps)
- **Fetch per-user reports** for the last _N_ seconds
- **View analytics chart** (events per user) as an HTML page
- **Trigger an outbound phone call** via **Bland.ai** (optional)
- Includes **unit tests** (`pytest`) and a **load test** script (`scripts/load_test.py`)
- Opening the base URL (`/`) redirects straight to **Swagger docs** (`/docs`)

> Bland.ai calling requires a valid **BLAND_API_KEY** and an **E.164** phone number format. Check Bland.ai for supported regions.

---

## Quick start

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open:
- Docs (Swagger UI): `http://localhost:8000/docs` (also `http://localhost:8000/` redirects here)
- Chart: `http://localhost:8000/analytics/events-per-user`

---

## API Endpoints

Base URL (local): `http://localhost:8000`

### 1) `POST /events` — Record an event
**Request body (JSON):**
```json
{
  "user_id": "dudu",
  "event_name": "level2completed"
}
```

**Example**
```bash
curl -X POST "http://localhost:8000/events"   -H "Content-Type: application/json"   -d '{"user_id":"dudu","event_name":"level2completed"}'
```

---

### 2) `POST /events/reports` — Get user events in last N seconds
**Request body (JSON):**
```json
{
  "user_id": "dudu",
  "last_seconds": 200
}
```

**Example**
```bash
curl -X POST "http://localhost:8000/events/reports"   -H "Content-Type: application/json"   -d '{"user_id":"dudu","last_seconds":200}'
```

---

### 3) `GET /analytics/events-per-user` — Events per user chart
Returns an **HTML page** with a **PNG chart** (base64-embedded) showing **number of events per user**.

**Example**
Open in browser:
- `http://localhost:8000/analytics/events-per-user`

---

### 4) `POST /outreach/call` — Trigger an outbound phone call (Bland.ai)
**Request body (JSON):**
```json
{
  "phone_number": "+972501234567"
}
```

**Example**
```bash
curl -X POST "http://localhost:8000/outreach/call"   -H "Content-Type: application/json"   -d '{"phone_number":"+972501234567"}'
```

---

## Environment Variables

Create a `.env` file (not committed) or export variables in your shell.

**Required**
- `EVENTS_DB_PATH` – path to the sqlite file (example: `./events.db`)

**Required only for Bland.ai calling**
- `BLAND_API_KEY` – required for `POST /outreach/call`

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
It sends multiple `POST /events` requests in parallel using **joblib**.

### Run against local server
1) Start the server (local or Docker)  
2) Run:
```bash
python scripts/load_test.py
```

### Run against a different host
Set `BASE_URL` (the script appends `/events` automatically):
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
