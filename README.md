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
| GET    | `/tasks`          | List tasks. Optional filters, combined with AND — see below. |
| GET    | `/tasks/{id}`     | One task, or `404`.                                |
| PATCH  | `/tasks/{id}`     | Partial update. `404` unknown id, `409` illegal status move. |
| DELETE | `/tasks/{id}`     | `204` on success, `404` unknown id.                |

### `GET /tasks` filters

All filters are optional and combine with **AND**. No matches is `200` with an
empty array, never a `404`. An unknown enum value is `422`.

| Parameter  | Type            | Behaviour                                                        |
| ---------- | --------------- | ---------------------------------------------------------------- |
| `status`   | enum            | `todo` \| `in_progress` \| `done`                                |
| `priority` | enum            | `low` \| `medium` \| `high`                                      |
| `assignee` | string          | **Exact** match, case-insensitive. `Mar` does not match `Maria`. |
| `overdue`  | bool, tri-state | Omit for all; `true` for overdue only; `false` for everything else, including tasks with no due date. |
| `q`        | string ≤ 200    | Case-insensitive **substring** search over title and description. Whitespace-only is treated as no search. |

Example: `GET /tasks?q=auth&status=todo&priority=high&overdue=true`

### Task fields

`title` (required), `description`, `status`, `priority`, `assignee`,
`due_date`, plus the server-owned `id`, `created_at`, `updated_at`, and
`is_overdue`.

`due_date` is a calendar date (`YYYY-MM-DD`), not a timestamp, and is optional.
A date in the past is accepted — that is the case the overdue badge exists to
surface. On `PATCH`, sending `"due_date": null` clears it, while omitting the
key leaves it unchanged.

`is_overdue` is **derived by the server on every read** and never stored:

```
is_overdue = due_date is not None and due_date < today and status != done
```

A task due today is not overdue, and a `done` task is never overdue. The
backend owns this so the card badge and the `?overdue=` filter cannot disagree —
the frontend renders the boolean rather than doing date maths.

### Status transitions

A task moves one column at a time. `todo → done` is rejected with `409`;
reopening (`done → in_progress`) is allowed. See `app/business_rules.py`.

## Project layout

```
app/
  main.py             FastAPI app, task routes, CORS
  models.py           Pydantic request/response models
  storage.py          JSON file persistence + filtering
  business_rules.py   status transitions, overdue rule
  core/config.py      settings from environment / .env
  api/routes/health.py
frontend/
  index.html  styles.css  app.js
scripts/
  behavior_contract.py   diffable record of observable API behaviour
tests/
  conftest.py            shared fixtures (isolated temp store per test)
  test_health.py         smoke tests
  test_tasks_crud.py     CRUD contract
  test_business_rules.py status transitions
  test_due_dates.py      due dates + overdue filter
  test_search_filters.py search + combined filters
docs/midcourse/          mid-course project documentation
```

---

## Mid-course project

The `mid-course-project` branch adds two features to the Module 1–3 baseline:

1. **Due dates + overdue filter** — optional `due_date`, a server-derived
   `is_overdue` flag, due/overdue pills on cards, and an "Overdue only" filter.
2. **Search + combined filters** — `q` text search over title and description,
   combinable with status, priority, assignee and overdue, driven from a filter
   bar above the board.

Both are usable in the frontend. The suite went from **20 to 68 tests**
(48 new).

### Documentation

| File | Contents |
| ---- | -------- |
| [docs/midcourse/user-stories.md](docs/midcourse/user-stories.md) | 5 user stories per feature with acceptance criteria, and the AI assumptions I corrected |
| [docs/midcourse/mini-adr.md](docs/midcourse/mini-adr.md) | 8 decisions, the alternatives AI suggested, and what was rejected as out of scope |
| [docs/midcourse/prompt-log.md](docs/midcourse/prompt-log.md) | Prompts per feature, one weak prompt rewritten, and what I accepted / edited / rejected |
| [docs/midcourse/verification.md](docs/midcourse/verification.md) | Baseline, test results, manual browser checks, contract diff, and two Break Tests |
| [docs/midcourse/reflection.md](docs/midcourse/reflection.md) | What helped, what slowed me down, where review changed the result |
| `contract-before-refactor.txt` / `contract-after-refactor.txt` | The captures diffed across the refactor |

### Behaviour contract

Used to prove the refactor changed no behaviour. It drives the API through a
fixed script and prints every status code and result, with all dates relative to
today so the output is stable on any day:

```bash
python scripts/behavior_contract.py
```

Capture it before a refactor, capture it after, and diff the two. The committed
captures are byte-identical.
