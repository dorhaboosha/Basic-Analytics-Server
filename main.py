###### Our Names and IDs ######
# Moran Herzlinger - 314710500
# Dor Haboosha - 208663534
# Itay Golan - 206480402
#####################

from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from fastapi.responses import HTMLResponse
import requests


# Initialize the FastAPI app
app = FastAPI()


# Define the event model
class Event(BaseModel):
    userid: str
    eventname: str


class PhoneNumber(BaseModel):
    phone_number: str

# Database connection function
def get_db_connection():
    conn = sqlite3.connect('events.db')
    conn.row_factory = sqlite3.Row
    return conn


# Initialize the database and create the table
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS events (
            eventtimestamputc TEXT,
            userid TEXT,
            eventname TEXT
        )
    ''')
    conn.commit()
    conn.close()


# Call the database initialization on startup
init_db()


# Process event method
@app.post("/process_event")
async def process_event(event: Event):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO events (eventtimestamputc, userid, eventname)
        VALUES (?, ?, ?)
    ''', (datetime.utcnow().isoformat(), event.userid, event.eventname))
    conn.commit()
    conn.close()
    return {"status": "event recorded"}


# Get reports method
@app.post("/get_reports")
async def get_reports(lastseconds: int, userid: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Calculate the datetime X seconds ago
    from_datetime = datetime.utcnow() - timedelta(seconds=lastseconds)

    # Query events for the given userid within the specified timeframe
    cursor.execute('''
        SELECT * FROM events 
        WHERE userid = ? AND eventtimestamputc >= ?
    ''', (userid, from_datetime.isoformat()))
    rows = cursor.fetchall()

    conn.close()

    # Convert rows to dictionary format
    reports = [{"eventtimestamputc": row["eventtimestamputc"], "userid": row["userid"], "eventname": row["eventname"]}
               for row in rows]

    return {"reports": reports}



#Use BlandAI to make a call to the user and try to sell him the API server.
def phone_caller(phone_number):
    my_api_key = "sk-jtltu0loqqvchajncpra9g0jt36dk86q8uo1gfojggtg0ck9byg6trmyutffgqny69"
    headers = {
        'Authorization': my_api_key
    }

    data = {
        "phone_number": f'{phone_number}',
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
        "voice_id": 2,
        "max_duration": {"seconds": 60}
    }

    requests.post('https://api.bland.ai/call', json=data, headers=headers)

#Make a post request to the server to call the user.
@app.post("/call_user")
async def call_user(phone_number: PhoneNumber):
    phone_caller(phone_number.phone_number)
    return "Calling"

#Create an image of chart of the number of events per user.
def generate_event_chart():
    conn = get_db_connection()
    cursor = conn.cursor()
    col = ['time', 'userid', 'eventname']

    # Query all events from the table
    cursor.execute('''
            SELECT * FROM events
        ''')
    rows = cursor.fetchall()

    conn.close()

    df = pd.DataFrame(rows, columns=col)

    event_counts = df['userid'].value_counts()

    # Create a bar chart
    plt.figure(figsize=(10, 6))
    event_counts.plot(kind='bar')
    plt.xlabel('User ID')
    plt.ylabel('Number of Events')
    plt.title('Number of Events per User')
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()

    # Return the base64 encoded image
    return image_base64

#Create a get request to the server to get the chart of the number of events per user.
@app.get("/analyze_events", response_class=HTMLResponse)
async def analyze_events():
    image_base64 = generate_event_chart()

    # Ensure the base64 string is complete and correct
    # The string should start with 'data:image/png;base64,' if it's a png image
    if not image_base64.startswith('data:image'):
        image_base64 = 'data:image/png;base64,' + image_base64

    # Create an HTML content with the image embedded
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

