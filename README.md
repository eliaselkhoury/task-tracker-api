# Task Tracker API

A small task tracker built for the AUB AI-assisted development course: a
FastAPI backend with JSON file storage, and a plain HTML/CSS/JS Kanban board
frontend.

- **Backend** — FastAPI + Pydantic, tasks persisted to a JSON file.
- **Frontend** — one `index.html` / `styles.css` / `app.js`, no framework or build step.
- **Tests** — pytest against the API through FastAPI's `TestClient`.

---

## Final Project

Branch reviewed: **`final-project`**

### What this submission demonstrates

- The existing Task Tracker still runs, inside the intended course scope. No
  product feature was added; `scripts/behavior_contract.py` produces output
  identical to the committed capture in
  [docs/midcourse/contract-current.txt](docs/midcourse/contract-current.txt),
  apart from the 3-byte UTF-8 BOM that capture carries from having been written
  by PowerShell.
- CI runs the pytest suite on push and on pull request.
- The Docker image builds and runs, with `/health` returning `200`.
- AI review, security and ownership evidence is in `docs/`.

### How to run locally

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app
```

(macOS/Linux: `source venv/bin/activate`.) The API is then on
<http://127.0.0.1:8000>, and `/health` returns
`{"status":"ok","service":"task-tracker-api"}`.

For the board, serve the frontend in a second terminal and open
<http://127.0.0.1:5500>:

```bash
python scripts/serve_frontend.py
```

### How to run tests

```bash
pytest
```

91 tests. Each one runs against its own temporary JSON store, so the suite never
touches `data/tasks.json`.

### How to run with Docker

```bash
docker build -t task-tracker-api .
```

```bash
docker run --rm -p 8000:8000 --name task-tracker task-tracker-api
```

```bash
curl -i http://127.0.0.1:8000/health
```

On Windows PowerShell, `curl` is an alias for `Invoke-WebRequest`, so use:

```bash
(Invoke-WebRequest http://127.0.0.1:8000/health).StatusCode
```

The image is the **API only**. The frontend is static and is served separately,
exactly as it is in local development — making FastAPI serve it would be a
product change, and this project does not add features. Tasks created inside the
container live in the container and disappear with `--rm`; mount a volume with
`-v "${PWD}/data:/app/data"` if you want them to survive.

### Evidence files

- [docs/release-evidence.md](docs/release-evidence.md) — baseline, CI, Docker,
  and the documentation claim-vs-reality log.
- [docs/final-ai-review.md](docs/final-ai-review.md) — graded AI code review and
  security review, the manual checks, and the ownership statement.
- [docs/ai-playbook.md](docs/ai-playbook.md) — the rules I will use with AI after
  the course.

### AI assistance summary

AI helped draft or review: the CI workflow, the Dockerfile and `.dockerignore`,
`AGENTS.md`, the documentation, and two read-only review passes (code review of
the release diff, and a security review of the repo).

I verified the work by: running the full pytest suite (91 passed), curling
`/health`, opening the board and exercising the create/edit modal, diffing
`scripts/behavior_contract.py` output against the committed capture, building and
running the container, watching CI go green, and re-deriving every AI finding
against the actual file before recording a grade for it.

One AI suggestion I rejected or corrected: see the "One AI output I rejected or
corrected" section of [docs/final-ai-review.md](docs/final-ai-review.md).

---

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
(it uses port 5500), or serve the folder with the included dev server:

```bash
python scripts/serve_frontend.py
```

Then open <http://127.0.0.1:5500>.

> **Use one of those two, not `python -m http.server`.** `http.server` sends
> `Last-Modified` but no `Cache-Control` and no `ETag`, so browsers apply
> heuristic caching and serve a stale `styles.css` or `app.js` without
> revalidating. You edit a file, reload, and see the old page — which is
> indistinguishable from your change not working. `scripts/serve_frontend.py` is
> the same static server with `Cache-Control: no-store` added; Live Server does
> not have the problem either. If you do use `http.server`, hard-reload
> (<kbd>Ctrl</kbd>+<kbd>F5</kbd>) after every edit.

Both ports are pre-approved in `CORS_ORIGINS` (see `.env.example`). The
frontend expects the API at `http://127.0.0.1:8000`, set in `API_BASE` at the
top of `frontend/app.js`.

## Open in VS Code

Open the `task-tracker-api` folder itself, not its parent — pytest discovery and
the relative paths in `.vscode/` depend on it being the workspace root:

```bash
code task-tracker-api
```

`.vscode/` is committed, so on first open VS Code offers the three recommended
extensions (Python, Pylance, Live Server), selects `venv` as the interpreter, and
picks up these run configurations from the Run and Debug panel:

| Configuration | What it does |
| ------------- | ------------ |
| **Backend + Frontend** | Compound — starts both servers, then open <http://127.0.0.1:5500> |
| **Backend: uvicorn** | API on port 8000, no reloader (see the note below) |
| **Backend: uvicorn --reload** | Same, with auto-reload |
| **Frontend: dev server (no cache)** | `scripts/serve_frontend.py` on port 5500 |
| **Behaviour contract** | Runs `scripts/behavior_contract.py` |
| **Debug the current test file** | pytest on the open file, with breakpoints |

`Ctrl+Shift+P` → *Tasks: Run Task* also has **Tests: run all** and
**Contract: compare against the committed capture** (which should print nothing).

Live Server is configured to serve `frontend/` as the site root, so the page is
at `http://127.0.0.1:5500/` rather than `/frontend/index.html`.

> **On `--reload`:** on the machine this was developed on, uvicorn's reloader
> detected one file change and then silently stopped watching, so the server kept
> serving stale code while pytest passed against the new code. The default
> **Backend: uvicorn** config omits `--reload` for that reason. If a live
> response ever disagrees with a passing test, restart the server before
> suspecting your code.

On macOS or Linux, change `python.defaultInterpreterPath` in
`.vscode/settings.json` to `${workspaceFolder}/venv/bin/python`.

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
| PATCH  | `/tasks/{id}`     | Partial update. `404` unknown id, `409` illegal status move, `422` invalid field value. |
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

### What `null` means in a PATCH

Only the genuinely optional fields can be cleared:

| Field | `PATCH {"field": null}` |
| ----- | ----------------------- |
| `description`, `assignee`, `due_date` | `200` — the value is cleared |
| `title`, `status`, `priority` | `422` — a task always has these; omit the key to leave one unchanged |

A rejected update writes **nothing** to `data/tasks.json`. `update_task` builds
the merged record, validates it, and only saves if validation passes — so a bad
request can never leave a task on disk that later reads would choke on.

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
  serve_frontend.py      static dev server with caching disabled
tests/
  conftest.py                 shared fixtures (isolated temp store per test)
  test_health.py              smoke tests
  test_tasks_crud.py          CRUD contract
  test_business_rules.py      status transitions
  test_due_dates.py           due dates + overdue filter
  test_search_filters.py      search + combined filters
  test_update_null_fields.py  what null means in a PATCH
docs/
  midcourse/                  mid-course project documentation
  release-evidence.md         final project: baseline, CI, Docker, doc claims
  final-ai-review.md          final project: graded AI review + ownership
  ai-playbook.md              final project: my rules for working with AI
.github/workflows/ci.yml      pytest on push and pull request
Dockerfile                    API-only image, non-root
.dockerignore                 keeps .env, data/, venv/ out of the build context
AGENTS.md                     guardrails for AI agents working in this repo
```

---

## Mid-course project

The `mid-course-project` branch adds two features to the Module 1–3 baseline:

1. **Due dates + overdue filter** — optional `due_date`, a server-derived
   `is_overdue` flag, due/overdue pills on cards, and an "Overdue only" filter.
2. **Search + combined filters** — `q` text search over title and description,
   combinable with status, priority, assignee and overdue, driven from a filter
   bar above the board.

Both are usable in the frontend. The suite went from **20 to 91 tests**
(71 new) — 48 for the two features, plus 23 covering a data-corruption bug found
in review and fixed (see §7 of `verification.md`).

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
