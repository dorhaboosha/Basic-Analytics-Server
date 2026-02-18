"""
Basic Analytics Server — FastAPI application for event tracking, reporting, and outreach.

This module provides:
- Event ingestion: record user events via POST /events
- Event reports: fetch events for a user in a time window via POST /events/reports
- Outbound calls: trigger a Bland AI sales call via POST /outreach/call (requires BLAND_API_KEY)
- Event analytics: view a bar chart of events per user via GET /analytics/events-per-user
- Root redirect: GET / redirects to /docs

Configuration is read from a .env file in the project directory.
The SQLite database path can be overridden with EVENTS_DB_PATH (default: events.db next to this file).
"""

from __future__ import annotations

import base64
import io
import logging
import os
import re
import sqlite3
import threading
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

import matplotlib.pyplot as plt
import pandas as pd
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Load environment variables from a local ".env" file reliably.
# -----------------------------------------------------------------------------
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
DB_PATH = os.getenv("EVENTS_DB_PATH", str(Path(__file__).resolve().parent / "events.db"))
_current_db_path: str = DB_PATH

# Simple E.164 phone validation: + + 8-16 digits total (first digit 1-9)
E164_REGEX = re.compile(r"^\+[1-9]\d{7,15}$")

# Limit chart to recent data to avoid unbounded memory use
CHART_DAYS = 90
CHART_ROW_LIMIT = 100_000

# Serialize matplotlib use (not thread-safe)
_chart_lock = threading.Lock()

# -----------------------------------------------------------------------------
# API Schemas (Docs-Friendly)
# -----------------------------------------------------------------------------
class EventIn(BaseModel):
    """Request body for recording a single analytics event."""

    user_id: str = Field(..., description="Unique identifier of the user who triggered the event.", max_length=256)
    event_name: str = Field(..., description="Name of the event (e.g., 'signup', 'purchase').", max_length=256)


class EventRecordedOut(BaseModel):
    """Response returned after an event is successfully recorded."""

    status: str = Field(..., description="Operation result message.")


class ReportsRequest(BaseModel):
    """Request body for fetching recent events for a specific user."""

    user_id: str = Field(..., description="User identifier to fetch events for.")
    last_seconds: int = Field(..., gt=0, description="Time window in seconds (e.g., 3600 for last hour).")


class ReportItem(BaseModel):
    """Single event record returned in reports."""

    event_timestamp_utc: str = Field(..., description="UTC timestamp (ISO 8601) when the event was recorded.")
    user_id: str = Field(..., description="User identifier.")
    event_name: str = Field(..., description="Event name.")


class ReportsOut(BaseModel):
    """Response body for reports endpoint."""

    reports: List[ReportItem] = Field(..., description="List of event records in the requested time window.")


class CallUserRequest(BaseModel):
    """Request body for initiating an outbound call using Bland AI."""

    phone_number: str = Field(..., description="E.164 phone format, e.g. +972501234567")


class CallUserOut(BaseModel):
    """Response returned after call request is accepted."""

    status: str = Field(..., description="Operation result message.")
    bland_response: Dict[str, Any] = Field(..., description="Raw response from Bland AI API.")


# -----------------------------------------------------------------------------
# DB helpers
# -----------------------------------------------------------------------------
@contextmanager
def get_db_connection():
    """
    Yield a SQLite connection; automatically closed on exit.

    - Uses _current_db_path (set by create_app or default DB_PATH).
    - Rows are sqlite3.Row dict-like objects.
    """
    conn = sqlite3.connect(_current_db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """
    Create the events table if it does not exist.

    Table schema:
      - eventtimestamputc (TEXT)
      - userid            (TEXT)
      - eventname         (TEXT)
    """
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                eventtimestamputc TEXT,
                userid TEXT,
                eventname TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_userid_tstamp ON events(userid, eventtimestamputc)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_tstamp ON events(eventtimestamputc)")
        conn.commit()


# -----------------------------------------------------------------------------
# Lifespan
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure the events table exists on startup; no cleanup on shutdown."""
    app.state.db_path = _current_db_path
    init_db()
    yield


# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Basic Analytics Server",
    description=(
        "A simple analytics API for recording user events, generating reports, "
        "triggering outbound outreach calls via Bland AI, and viewing basic charts."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


def create_app(db_path: Optional[str] = None) -> FastAPI:
    """
    Return the FastAPI app, optionally configured to use a specific DB path.

    When db_path is provided (e.g. in tests), all DB access uses that path
    and app.state.db_path is set so callers can read it. When db_path is None,
    EVENTS_DB_PATH env or the default (events.db next to main.py) is used.
    """
    global _current_db_path
    _current_db_path = db_path if db_path is not None else DB_PATH
    app.state.db_path = _current_db_path
    return app


# -----------------------------------------------------------------------------
# Root redirect to docs
# -----------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect the root URL to the interactive API documentation."""
    return RedirectResponse(url="/docs")


# -----------------------------------------------------------------------------
# Internal logic helpers
# -----------------------------------------------------------------------------
def _insert_event(user_id: str, event_name: str) -> None:
    """Insert a single event row with current UTC timestamp."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO events (eventtimestamputc, userid, eventname)
            VALUES (?, ?, ?)
            """,
            (datetime.now(timezone.utc).isoformat(), user_id, event_name),
        )
        conn.commit()


def _fetch_reports(user_id: str, last_seconds: int) -> List[ReportItem]:
    """Fetch event rows for a user within the last N seconds and map them to ReportItem."""
    from_datetime = datetime.now(timezone.utc) - timedelta(seconds=last_seconds)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM events
            WHERE userid = ? AND eventtimestamputc >= ?
            """,
            (user_id, from_datetime.isoformat()),
        )
        rows = cursor.fetchall()

    return [
        ReportItem(
            event_timestamp_utc=row["eventtimestamputc"],
            user_id=row["userid"],
            event_name=row["eventname"],
        )
        for row in rows
    ]


def phone_caller(phone_number: str) -> Dict[str, Any]:
    """
    Initiate a Bland AI sales call to the given E.164 phone number.

    Requires:
      - BLAND_API_KEY in environment (.env or container env var)

    Raises:
      - RuntimeError for validation / external API errors
    """
    api_key = os.getenv("BLAND_API_KEY")
    if not api_key:
        raise RuntimeError("Missing BLAND_API_KEY. Set it in .env (local) or as an env var in Docker.")

    api_key = api_key.strip().strip('"').strip("'")

    if not E164_REGEX.match(phone_number):
        raise RuntimeError("phone_number must be in E.164 format, e.g. +972501234567")

    headers = {"Authorization": api_key}
    data = {
        "phone_number": phone_number,
        "task": """You are an API server sales agent.
You need to call clients and explain them about the benefits of using our API server.
Tell them that our API server is precise and have fast response times, and got the ability to handle a large number of requests into the database.
You should explain the user something about the current data and the potential of the API server.
Try to convince him to become a paying user of the our analytics server, and tell him that he will get a 20% discount if he signs up today.
You should also tell him that he can get a free trial for 30 days.
If the user is interested, you should ask him for his email address and send him an email with the details of the offer.
""",
        "model": "base",
        "reduce_latency": True,
        "voice": "4e65cda2-cf46-4907-84ba-3ca96c48f549",
        "max_duration": 60,
    }

    resp = requests.post("https://us.api.bland.ai/v1/calls", json=data, headers=headers, timeout=30)
    if resp.status_code >= 400:
        raise RuntimeError(f"BlandAI call failed: {resp.status_code} - {resp.text}")

    return resp.json()


def generate_event_chart() -> Optional[str]:
    """
    Build a bar chart of event counts per user from recent events.

    Returns:
      - base64 PNG string (no prefix), or None if no data exists.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        since = (datetime.now(timezone.utc) - timedelta(days=CHART_DAYS)).isoformat()
        cursor.execute(
            """
            SELECT eventtimestamputc, userid, eventname FROM events
            WHERE eventtimestamputc >= ?
            ORDER BY eventtimestamputc DESC
            LIMIT ?
            """,
            (since, CHART_ROW_LIMIT),
        )
        rows = cursor.fetchall()

    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["eventtimestamputc", "userid", "eventname"])
    if df.empty:
        return None

    event_counts = df["userid"].value_counts()

    with _chart_lock:
        fig, ax = plt.subplots(figsize=(10, 6))
        try:
            event_counts.plot(kind="bar", ax=ax)
            ax.set_xlabel("User ID")
            ax.set_ylabel("Number of Events")
            ax.set_title("Number of Events per User")
            fig.tight_layout()

            buf = io.BytesIO()
            fig.savefig(buf, format="png")
            buf.seek(0)
            image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            buf.close()
        finally:
            plt.close(fig)

    return image_base64


# -----------------------------------------------------------------------------
# Endpoints (new only)
# -----------------------------------------------------------------------------
@app.post(
    "/events",
    summary="Record an event",
    description="Stores a single analytics event in SQLite with the current UTC timestamp.",
    tags=["Events"],
    response_model=EventRecordedOut,
)
def record_event(event: EventIn) -> EventRecordedOut:
    _insert_event(event.user_id, event.event_name)
    return EventRecordedOut(status="event recorded")


@app.post(
    "/events/reports",
    summary="Get user events in a recent time window",
    description="Returns all events recorded for a user within the last N seconds.",
    tags=["Events"],
    response_model=ReportsOut,
)
def get_user_event_reports(payload: ReportsRequest) -> ReportsOut:
    reports = _fetch_reports(payload.user_id, payload.last_seconds)
    return ReportsOut(reports=reports)


@app.post(
    "/outreach/call",
    summary="Trigger an outbound sales call",
    description="Initiates a Bland AI call to the given phone number. Requires BLAND_API_KEY in environment.",
    tags=["Outreach"],
    response_model=CallUserOut,
)
def trigger_outbound_call(payload: CallUserRequest) -> CallUserOut:
    try:
        result = phone_caller(payload.phone_number)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in trigger_outbound_call")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.") from e

    return CallUserOut(status="calling", bland_response=result)


@app.get(
    "/analytics/events-per-user",
    summary="View event volume per user (chart)",
    description="Returns an HTML page displaying a bar chart of event counts per user (recent data only).",
    tags=["Analytics"],
    response_class=HTMLResponse,
)
def view_events_per_user_chart() -> HTMLResponse:
    image_base64 = generate_event_chart()

    if not image_base64:
        return HTMLResponse(
            """
            <html>
                <head><title>Events per User</title></head>
                <body align="center">
                    <h3>No events found yet.</h3>
                </body>
            </html>
            """
        )

    image_src = "data:image/png;base64," + image_base64
    html_content = f"""
    <html>
        <head>
            <title>Events per User</title>
        </head>
        <body align="center">
            <h2>Number of Events per User</h2>
            <img src="{image_src}" alt="Events per User">
        </body>
    </html>
    """
    return HTMLResponse(html_content)
