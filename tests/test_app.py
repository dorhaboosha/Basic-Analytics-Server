"""
Pytest tests for the Basic Analytics Server FastAPI app.

Covers: POST /process_event, POST /get_reports, POST /call_user (missing-api-key path).
Uses a temporary SQLite DB per test via the client fixture; BLAND_API_KEY is not required
except in test_call_user_without_key_returns_400 where we assert its absence.
"""

import os
import importlib
import sqlite3
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """
    Creates a fresh app client using a temporary sqlite DB for each test.
    This keeps tests isolated and prevents touching a real events.db.
    """
    test_db_path = tmp_path / "test_events.db"
    monkeypatch.setenv("EVENTS_DB_PATH", str(test_db_path))

    # Import (or reload) main AFTER setting env var so it picks up EVENTS_DB_PATH
    import main
    importlib.reload(main)

    with TestClient(main.app) as c:
        yield c


def test_process_event_inserts_row(client):
    """POST /process_event with valid JSON returns 200 and persists the event in the DB."""
    resp = client.post("/process_event", json={"userid": "test_user", "eventname": "test_event"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "event recorded"}

    # Verify the DB row exists (read the DB file used by the app)
    import main
    conn = sqlite3.connect(main.DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT userid, eventname FROM events WHERE userid=? AND eventname=?", ("test_user", "test_event"))
    row = cur.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "test_user"
    assert row[1] == "test_event"


def test_invalid_event_data_returns_422(client):
    """POST /process_event with structurally invalid payload (missing required field) returns 422."""
    resp = client.post("/process_event", json={"userid": "u1"})  # missing "eventname"
    assert resp.status_code == 422


def test_get_reports_returns_events(client):
    """POST /get_reports for a user with an event in the last N seconds returns that event in reports."""
    # Insert an event
    client.post("/process_event", json={"userid": "u1", "eventname": "e1"})

    # Fetch reports
    resp = client.post("/get_reports", params={"lastseconds": 60, "userid": "u1"})
    assert resp.status_code == 200

    body = resp.json()
    assert "reports" in body
    assert isinstance(body["reports"], list)
    assert len(body["reports"]) >= 1
    assert body["reports"][0]["userid"] == "u1"


def test_call_user_without_key_returns_400(tmp_path, monkeypatch):
    """
    Ensure missing BLAND_API_KEY is handled.
    We force BLAND_API_KEY to be empty BEFORE importing main,
    so load_dotenv() will not override it from .env.
    """
    test_db_path = tmp_path / "test_events.db"
    monkeypatch.setenv("EVENTS_DB_PATH", str(test_db_path))

    # Important: set to empty string (so dotenv won't override)
    monkeypatch.setenv("BLAND_API_KEY", "")

    import main
    importlib.reload(main)

    with TestClient(main.app) as client:
        resp = client.post("/call_user", json={"phone_number": "+14155552671"})
        assert resp.status_code == 400
        assert "Missing BLAND_API_KEY" in resp.text

