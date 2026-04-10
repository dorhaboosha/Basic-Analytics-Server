"""
Tests for the Basic Analytics Server FastAPI app (new endpoints).

What’s covered:
- Events: POST /events
- Reports: POST /events/reports
- Outreach: POST /outreach/call (missing BLAND_API_KEY path)

Test isolation:
- Each test uses its own temporary SQLite database file via create_app(db_path).
- Tests do not rely on importlib.reload or module-level DB_PATH state.
"""

import sqlite3

import pytest
from fastapi.testclient import TestClient

import main


def _fetch_one_event(db_path: str, user_id: str, event_name: str):
    """
    Helper to verify persistence by reading SQLite directly.

    Why direct DB access?
    - It proves the API call resulted in a committed row (not just a 200 response).
    - It keeps the assertion targeted: one row, one query.
    """
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT userid, eventname FROM events WHERE userid=? AND eventname=?",
            (user_id, event_name),
        )
        return cur.fetchone()
    finally:
        conn.close()


@pytest.fixture()
def client(tmp_path):
    """
    TestClient configured with an isolated SQLite DB.

    Using create_app(db_path=...) keeps DB configuration explicit and avoids
    relying on module-level globals during tests.
    """
    test_db_path = tmp_path / "test_events.db"
    app = main.create_app(db_path=str(test_db_path))
    with TestClient(app) as c:
        yield c


# ---- Events -----------------------------------------------------------------
def test_record_event_inserts_row(client):
    """POST /events with valid JSON returns 200 and persists the event in the DB."""
    resp = client.post("/events", json={"user_id": "test_user", "event_name": "test_event"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "event recorded"}

    # Verify persistence by querying the same DB file the app was configured with.
    db_path = client.app.state.db_path
    row = _fetch_one_event(db_path, user_id="test_user", event_name="test_event")

    assert row is not None
    assert row[0] == "test_user"
    assert row[1] == "test_event"


def test_record_event_invalid_payload_returns_422(client):
    """POST /events with invalid payload (missing required field) returns 422."""
    # Missing required field "event_name" should fail request validation.
    resp = client.post("/events", json={"user_id": "u1"})
    assert resp.status_code == 422


# ---- Reports ----------------------------------------------------------------
def test_get_user_event_reports_returns_events(client):
    """POST /events/reports returns events for a user within the last N seconds."""
    # Arrange: insert an event.
    client.post("/events", json={"user_id": "u1", "event_name": "e1"})

    # Act: fetch reports (endpoint uses JSON body).
    resp = client.post("/events/reports", json={"user_id": "u1", "last_seconds": 60})
    assert resp.status_code == 200

    # Assert: event is present in the response.
    body = resp.json()
    assert "reports" in body
    assert isinstance(body["reports"], list)
    assert len(body["reports"]) >= 1
    assert body["reports"][0]["user_id"] == "u1"
    assert body["reports"][0]["event_name"] == "e1"


# ---- Outreach ---------------------------------------------------------------
def test_trigger_outbound_call_without_key_returns_400(tmp_path, monkeypatch):
    """
    Missing BLAND_API_KEY should be treated as a client error (400).

    We set BLAND_API_KEY to an empty string to ensure the code path that checks
    the environment is exercised (and .env values cannot override it).
    """
    test_db_path = tmp_path / "test_events.db"
    monkeypatch.setenv("BLAND_API_KEY", "")

    app = main.create_app(db_path=str(test_db_path))
    with TestClient(app) as client:
        resp = client.post("/outreach/call", json={"phone_number": "+14155552671"})
        assert resp.status_code == 400
        assert "Missing BLAND_API_KEY" in resp.text
