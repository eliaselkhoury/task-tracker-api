# AGENTS.md — instructions for AI coding agents in this repo

Read this before proposing or making any change. It is written for an agent,
but a human joining the project can read it as the short version of the rules.

## Stack

| Piece | What it actually is |
| ----- | ------------------- |
| Language | Python **3.12** (`python:3.12-slim` in the `Dockerfile`, `3.12` in CI, 3.12.10 on the dev machine) |
| API | FastAPI 0.115.6 |
| Validation | Pydantic **v2** (2.10.4) + pydantic-settings |
| Server | uvicorn 0.34.0 |
| Storage | a single JSON file — `data/tasks.json`. There is no database. |
| Tests | pytest 8.3.4 with FastAPI's `TestClient` (httpx) |
| Frontend | one `index.html` + `styles.css` + `app.js`. No framework, no build step, no npm. |

Exact pinned versions live in `requirements.txt`. Do not upgrade or add a
dependency as a side effect of some other change.

## Run and test commands

```bash
# API, on http://127.0.0.1:8000 (deliberately without --reload — see the note
# at the end of this file)
uvicorn app.main:app

# Frontend, on http://127.0.0.1:5500
python scripts/serve_frontend.py

# Tests — the whole suite, from the repo root
pytest

# Observable-behaviour capture, for diffing across a refactor
python scripts/behavior_contract.py

# Container
docker build -t task-tracker-api .
docker run --rm -p 8000:8000 --name task-tracker task-tracker-api
```

## Read first, then write

Before editing anything:

1. **Read `README.md`** for the API contract, and the `docs/midcourse/`
   documents for *why* the current behaviour is the way it is. Several rules
   that look arbitrary (dates in the past are accepted; `assignee` is an exact
   match while `q` is a substring search) were decided deliberately and are
   recorded in `docs/midcourse/mini-adr.md`.
2. **Read the file you are about to change, in full.** The comments in
   `app/storage.py` and `app/models.py` explain bugs that were already found
   and fixed once; a "cleanup" that deletes them tends to reintroduce the bug.
3. **Check `tests/` for the behaviour you are about to change.** 91 tests
   describe the contract. If a change makes a test fail, the default assumption
   is that the change is wrong, not the test.
4. If the docs and the code disagree, **say so and stop.** Do not silently pick
   one. That disagreement is the finding.

## Do not touch `app/` or `frontend/` without a reason you can name

This repo is in maintenance, not development. `app/` and `frontend/` may only
change for:

- a bug fix with a failing test that proves the bug first, or
- a security fix, or
- a correction that the documentation already calls for.

Anything else — new endpoints, authentication, a real database, comments,
notifications, reordering the UI, a CSS refresh, swapping vanilla JS for a
framework — is **out of scope**. If you think one is needed, write it down as a
suggestion; do not implement it.

Every change to `app/` or `frontend/` made during the final project must be
explained in `docs/final-ai-review.md`. An unexplained diff in those directories
is a defect regardless of whether the code is good.

## Project rules

- **Status values are `todo`, `in_progress`, `done`** — lowercase, snake_case,
  on the wire and in storage. `ToDo` / `In Progress` / `Done` are *display
  labels in the frontend only*. Do not "fix" the API to match the labels.
- **Priority values are `low`, `medium`, `high`.** Same rule.
- A task moves one column at a time. `todo → done` is a `409`. Reopening
  (`done → in_progress`) is allowed. See `app/business_rules.py`.
- **`is_overdue` is derived on every read and never stored.** A stored copy is
  wrong the next morning. The backend owns the rule so the card badge and the
  `?overdue=` filter cannot disagree.
- **Validate before writing.** `storage.update_task` builds a merged candidate,
  validates it, and only then saves. A rejected request must leave
  `data/tasks.json` byte-for-byte unchanged. This is not stylistic: the earlier
  version wrote first and corrupted the store.
- **Preserve existing response shapes and status codes** unless the change is
  the explicit point of the task. `404` unknown id, `409` illegal transition,
  `422` invalid field value, `204` on delete.
- No matches on a filtered list is `200` with `[]`, never `404`.

## Secrets and data

- Never put a real credential, token, `.env` value, production log, or real
  personal/customer data into this repo, into a prompt, or into a commit
  message. `.env` and `data/` are gitignored and excluded from the Docker build
  context — keep it that way.
- `.env.example` holds placeholder values only.
- `data/tasks.json` is local runtime state, not source. Do not commit it and do
  not read from it when a test fixture would do.

## Tests

- Every fix gets a test that fails before it and passes after.
- Tests must not depend on the real clock or the developer's data file.
  `tests/conftest.py` already redirects storage to a temp file per test and
  `business_rules.is_task_overdue` takes an injectable `reference_date`.
- Do not weaken an assertion to make a suite green.

## Definition of done for any change here

1. `pytest` passes locally — all of it, not the subset you touched.
2. `python scripts/behavior_contract.py` still matches the committed capture,
   unless changing behaviour was the point.
3. The diff contains nothing you cannot explain line by line.
4. CI (`.github/workflows/ci.yml`) is green on the pushed branch.

## One local quirk worth knowing

`uvicorn --reload` has, on this machine, detected one file change and then
silently stopped watching — the server kept serving stale code while pytest
passed against the new code. **If a live response disagrees with a passing
test, restart the server before you suspect the code.**
