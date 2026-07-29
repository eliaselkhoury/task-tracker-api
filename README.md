# Task Tracker API

A small task tracker built for the AUB AI-assisted development course: a
FastAPI backend with JSON file storage, and a plain HTML/CSS/JS Kanban board
frontend.

- **Backend** — FastAPI + Pydantic, tasks persisted to a JSON file.
- **Frontend** — one `index.html` / `styles.css` / `app.js`, no framework or build step.
- **Tests** — pytest against the API through FastAPI's `TestClient`.

## Requirements

- Python 3.12+
- A static file server for the frontend (VS Code **Live Server**, or Python's
  built-in `http.server` — see below)

## Setup

```bash
python -m venv venv
```

Activate it:

```bash
venv\Scripts\activate
```

(macOS/Linux: `source venv/bin/activate`)

Install dependencies:

```bash
pip install -r requirements.txt
```

Optionally copy the sample environment file and edit it:

```bash
copy .env.example .env
```

## Run the backend

```bash
uvicorn app.main:app --reload
```

The API is then on <http://127.0.0.1:8000>, with interactive docs at
<http://127.0.0.1:8000/docs> and a health check at
<http://127.0.0.1:8000/health>.

## Open the frontend

The frontend must be served over `http://`, not opened as a `file://` path —
a `file://` page has a null origin and the browser blocks its API calls.

Either open `frontend/index.html` with VS Code's **Live Server** extension
(it uses port 5500), or serve the folder yourself:

```bash
python -m http.server 5500 --directory frontend
```

Then open <http://127.0.0.1:5500>.

Both ports are pre-approved in `CORS_ORIGINS` (see `.env.example`). The
frontend expects the API at `http://127.0.0.1:8000`, set in `API_BASE` at the
top of `frontend/app.js`.

## Run the tests

```bash
pytest
```

Each test runs against its own temporary JSON store, so the suite never
touches `data/tasks.json`.

## API

| Method | Path              | Notes                                              |
| ------ | ----------------- | -------------------------------------------------- |
| GET    | `/health`         | Liveness check.                                    |
| POST   | `/tasks`          | Create a task. `201` on success, `422` on bad input. |
| GET    | `/tasks`          | List tasks. Optional `status`, `priority`, `assignee` filters (AND). |
| GET    | `/tasks/{id}`     | One task, or `404`.                                |
| PATCH  | `/tasks/{id}`     | Partial update. `404` unknown id, `409` illegal status move. |
| DELETE | `/tasks/{id}`     | `204` on success, `404` unknown id.                |

### Status transitions

A task moves one column at a time. `todo → done` is rejected with `409`;
reopening (`done → in_progress`) is allowed. See `app/business_rules.py`.

## Project layout

```
app/
  main.py             FastAPI app, task routes, CORS
  models.py           Pydantic request/response models
  storage.py          JSON file persistence
  business_rules.py   status-transition rules
  core/config.py      settings from environment / .env
  api/routes/health.py
frontend/
  index.html  styles.css  app.js
tests/
  conftest.py  test_health.py  test_tasks_crud.py  test_business_rules.py
```
