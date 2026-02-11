# Basic Analytics Server — production image for the FastAPI app.
#
# Build:  docker build -t basic-analytics-server .
# Run:    docker run -p 8000:8000 -e BLAND_API_KEY=your_key basic-analytics-server
#
# Optional env vars:
#   PORT          — port uvicorn listens on (default: 8000)
#   EVENTS_DB_PATH — path to SQLite DB file (default: /app/events.db)
#   BLAND_API_KEY — required for POST /call_user (Bland AI)
#
# Mount a volume for persistence:  -v /host/data:/app
# (then set EVENTS_DB_PATH=/app/events.db or use /app as working dir)
#
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV APP_HOME=/app

WORKDIR $APP_HOME

# Install dependencies first (better Docker caching)
COPY requirements.txt .
RUN python -m pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Run as non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN chown -R appuser:appgroup $APP_HOME
USER appuser

# Default port (platforms may override)
ENV PORT=8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
