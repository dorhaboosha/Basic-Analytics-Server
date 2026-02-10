from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from fastapi.responses import HTMLResponse
import requests
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# -----------------------------------------------------------------------------
# Load environment variables from a local ".env" file reliably.
# -----------------------------------------------------------------------------
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
# Allow overriding DB path (useful for tests + Docker volumes)
DB_PATH = os.getenv("EVENTS_DB_PATH", str(Path(__file__).resolve().parent / "events.db"))

# Simple E.164 phone validation: + + 8-16 digits total (first digit 1-9)
E164_REGEX = re.compile(r"^\+[1-9]\d{7,15}$")


# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------
class Event(BaseModel):
    userid: str
    eventname: str


class PhoneNumber(BaseModel):
    phone_number: str


# -----------------------------------------------------------------------------
# DB helpers
# -----------------------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            eventtimestamputc TEXT,
            userid TEXT,
            eventname TEXT
        )
        """
    )
    conn.commit()
    conn.close()


# -----------------------------------------------------------------------------
# Lifespan (replaces @app.on_event("startup"))
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown (nothing to clean up right now)


app = FastAPI(lifespan=lifespan)


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.post("/process_event")
async def process_event(event: Event):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO events (eventtimestamputc, userid, eventname)
        VALUES (?, ?, ?)
        """,
        (datetime.utcnow().isoformat(), event.userid, event.eventname),
    )
    conn.commit()
    conn.close()
    return {"status": "event recorded"}


@app.post("/get_reports")
async def get_reports(lastseconds: int, userid: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    from_datetime = datetime.utcnow() - timedelta(seconds=lastseconds)

    cursor.execute(
        """
        SELECT * FROM events
        WHERE userid = ? AND eventtimestamputc >= ?
        """,
        (userid, from_datetime.isoformat()),
    )
    rows = cursor.fetchall()
    conn.close()

    reports = [
        {
            "eventtimestamputc": row["eventtimestamputc"],
            "userid": row["userid"],
            "eventname": row["eventname"],
        }
        for row in rows
    ]

    return {"reports": reports}


def phone_caller(phone_number: str):
    api_key = os.getenv("BLAND_API_KEY")
    if not api_key:
        raise RuntimeError("Missing BLAND_API_KEY. Set it in .env (local) or as an env var in Docker.")

    # Clean/sanitize key (handles accidental quotes/spaces in .env)
    api_key = api_key.strip().strip('"').strip("'")

    # Validate phone number format (E.164), e.g. +972501234567
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


@app.post("/call_user")
async def call_user(phone_number: PhoneNumber):
    try:
        result = phone_caller(phone_number.phone_number)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    return {"status": "calling", "bland_response": result}


def generate_event_chart():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM events")
    rows = cursor.fetchall()
    conn.close()

    df = pd.DataFrame(rows, columns=["time", "userid", "eventname"])

    if df.empty or "userid" not in df.columns:
        return None

    event_counts = df["userid"].value_counts()

    plt.figure(figsize=(10, 6))
    event_counts.plot(kind="bar")
    plt.xlabel("User ID")
    plt.ylabel("Number of Events")
    plt.title("Number of Events per User")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    buf.close()

    return image_base64


@app.get("/analyze_events", response_class=HTMLResponse)
async def analyze_events():
    image_base64 = generate_event_chart()

    if not image_base64:
        return HTMLResponse(
            """
            <html>
                <head><title>Analyzed Events</title></head>
                <body align="center">
                    <h3>No events found yet.</h3>
                </body>
            </html>
            """
        )

    if not image_base64.startswith("data:image"):
        image_base64 = "data:image/png;base64," + image_base64

    html_content = f"""
    <html>
        <head>
            <title>Analyzed Events</title>
        </head>
        <body align="center">
            <img src="{image_base64}" alt="Analyzed Events">
        </body>
    </html>
    """
    return html_content
