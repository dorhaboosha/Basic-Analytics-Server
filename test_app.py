###### Our Names and IDs ######
# Moran Herzlinger - 314710500
# Dor Haboosha - 208663534
# Itay Golan - 206480402
#####################

import pytest
from fastapi.testclient import TestClient
from main import app, get_db_connection, init_db
import sqlite3
from unittest.mock import patch, MagicMock

# Create a test client
client = TestClient(app)
init_db()

# Define test cases
def test_process_event():
    # Arrange
    userid = "test_user"
    eventname = "test_event"
    response = client.post(
        "/process_event",
        json={"userid": userid, "eventname": eventname},
    )

    # Act
    conn = sqlite3.connect('events.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE userid = ? AND eventname = ?", (userid, eventname))
    data = cursor.fetchone()

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "event recorded"}
    assert data is not None
    assert data[1] == userid  # Accessing the userid at index 1
    assert data[2] == eventname  # Accessing the eventname at index 2

def test_invalid_event_data():
    # Test sending invalid event data to /process_event/
    invalid_event = {"userid": 123, "eventname": 456}  # Invalid data types
    response = client.post("/process_event", json=invalid_event)

    # Check if the response status code is 422 Unprocessable Entity (validation error)
    assert response.status_code == 422

    # Check if the response contains validation error details
    assert "userid" in response.text
    assert "eventname" in response.text


def test_get_db_connection():
    # Arrange
    mock_sqlite = MagicMock()
    mock_conn = MagicMock()
    mock_sqlite.connect.return_value = mock_conn

    # Act
    with patch('main.sqlite3', mock_sqlite):
        conn = get_db_connection()

    # Assert
    assert mock_sqlite.connect.call_count == 1  # Make sure connect method is called
    assert conn == mock_conn  # Ensure the connection returned is the mock connection

def test_init_db():
    # Arrange
    mock_sqlite = MagicMock()
    mock_conn = MagicMock()
    mock_sqlite.connect.return_value = mock_conn

    # Act
    with patch('main.sqlite3', mock_sqlite):
        init_db()

    # Assert
    assert mock_sqlite.connect.call_count == 1  # Make sure connect method is called
    assert mock_conn.execute.call_count == 1  # Make sure execute method is called
    assert mock_conn.commit.call_count == 1  # Make sure commit method is called
    assert mock_conn.close.call_count == 1  # Make sure close method is called

def test_get_reports():
    # Initialize the database (ensure it's in a clean state)
    init_db()

    # Insert test data into the database
    client.post("/process_event/", json={"userid": "test_user", "eventname": "test_event"})

    # Make a request to the /get_reports/ endpoint with query parameters
    response = client.post("/get_reports/?lastseconds=60&userid=test_user")

    # Check if the response status code is 200 OK
    assert response.status_code == 200

    # Additional assertions based on expected data
    # For example, check the response JSON content
    reports = response.json().get("reports", [])
    assert isinstance(reports, list)
    assert len(reports) > 0  # Ensure at least one report is returned

    # Check the structure of a report entry
    if reports:
        report = reports[0]
        assert isinstance(report, dict)
        assert "eventtimestamputc" in report
        assert "userid" in report
        assert "eventname" in report


if __name__ == "__main__":
    pytest.main()
