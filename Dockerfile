# Task Tracker API - container image for the backend only.
#
# The frontend is plain static files served separately (Live Server or
# scripts/serve_frontend.py). Teaching the FastAPI app to serve them would be a
# product change, and the final project is explicitly not adding features.

# Pinned to the minor version the project is developed and tested against, so
# the image, CI and my machine all agree. `python:3.12-slim` rather than
# `:latest`, so a new Python release cannot silently change the runtime.
FROM python:3.12-slim

# PYTHONDONTWRITEBYTECODE - no .pyc files in a layer that is never reused.
# PYTHONUNBUFFERED       - uvicorn logs reach `docker logs` immediately instead
#                          of sitting in a block buffer, which matters when the
#                          only debugging tool is the container's stdout.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies are copied and installed before the source so an edit to app/
# does not invalidate the pip layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only the API source. .dockerignore keeps .env, data/, venv/ and .git out of
# the build context entirely, so there is nothing secret to accidentally COPY.
COPY app/ ./app/

# The JSON store lives at <project root>/data/tasks.json, and the project root
# inside the image is /app. The directory has to exist and be writable by the
# non-root user before that user is switched to - a container that cannot write
# its own store fails on the first POST /tasks, not at startup.
#
# Non-root: if the app is ever exploited, the attacker lands as `appuser`, not
# as root inside the container.
#
# Only /app/data is handed to appuser. An earlier version did
# `chown -R appuser:appuser /app`, which also gave the runtime user write
# access to its own source - so anything able to write a file could rewrite
# app/main.py and have it executed on the next restart. The source stays
# root-owned and world-readable, which is all the app needs to import it.
RUN mkdir -p /app/data \
    && useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app/data
USER appuser

EXPOSE 8000

# Uses the stdlib rather than curl: `python:3.12-slim` has no curl, and adding
# one just for a health probe grows the image and its patch surface.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

# --host 0.0.0.0 so the published port reaches the process: bound to 127.0.0.1
# the server would only be visible from inside the container.
# No --reload: the reloader watches for source edits that cannot happen in an
# immutable image, and it has been unreliable on this project (see README).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
