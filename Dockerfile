# Basic Analytics Server — Docker image (FastAPI + SQLite)
#
# Quick start
# - Build:
#   docker build -t basic-analytics-server .
# - Run:
#   docker run -p 8000:8000 -e BLAND_API_KEY=your_key basic-analytics-server
#
# Environment variables
# - PORT: uvicorn port (default: 8000)
# - EVENTS_DB_PATH: SQLite DB path (default: /app/events.db)
# - BLAND_API_KEY: required for POST /outreach/call (Bland AI)
#
# Persistence
# - Mount /app to persist the DB:
#   docker run -p 8000:8000 -v /host/data:/app basic-analytics-server
#
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV APP_HOME=/app

WORKDIR $APP_HOME

# Dependencies (copy first for better Docker caching)
COPY requirements.txt .
RUN python -m pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Security: run as non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN chown -R appuser:appgroup $APP_HOME
USER appuser

# Runtime
ENV PORT=8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
