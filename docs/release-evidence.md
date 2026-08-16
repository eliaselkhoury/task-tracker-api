# Release Evidence

Everything below was run, not assumed. Commands are copied from the terminal
that produced the result.

## Baseline

Taken **before** any final-project change, on the branch point (`4d9547c`).

- **Branch:** `final-project`, cut from `main` at `4d9547c`
- **Date:** 2026-08-16
- **Local app run command:**
  ```
  venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
  ```
  (the README's documented form is `uvicorn app.main:app` with the venv active;
  deliberately without `--reload` — see the note at the end of the README)
- **`/health` result:** `200`
  ```
  STATUS: 200
  BODY: {"status":"ok","service":"task-tracker-api"}
  ```
- **Frontend check:** served with `python scripts/serve_frontend.py` and opened at
  <http://127.0.0.1:5500>. The Kanban board renders all three columns with their
  counts (ToDo 2, In Progress 3, Done 2), cards show priority and due/overdue
  pills, and the create/edit flow still works: **New Task** opens the modal with
  Title, Description, Status, Priority, Due date and Assignee, and **Cancel**
  closes it (`#modal-backdrop` regains its `hidden` attribute, computed
  `display: none`). Clicking **Edit** on "Renew SSL certificate" opens the modal
  populated with that task's real values.
- **Test command:** `pytest`
- **Test result:** `91 passed in 5.50s` — no failures, nothing skipped, nothing
  xfailed.
- **Scope check:** `python scripts/behavior_contract.py` produces output
  identical to the committed capture `docs/midcourse/contract-current.txt`,
  apart from the 3-byte UTF-8 BOM that file carries from having been written by
  PowerShell. Verified with a byte comparison, not by eye:
  ```
  committed starts with BOM : True
  fresh run starts with BOM : False
  identical after BOM strip : True
  size difference           : 3 bytes
  ```
  No product feature was added. The only change to a protected directory is one
  defence-in-depth escaping fix in `frontend/app.js`, explained in
  [final-ai-review.md](final-ai-review.md). `app/` is untouched.

**After** all final-project work: `91 passed in 4.28s`, and the behaviour
contract output is unchanged.

## CI evidence

- **Workflow file:** [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
- **Latest run:** **green** —
  <https://github.com/eliaselkhoury/task-tracker-api/actions/runs/31940098790>
  (run #4, commit `8e6eddf`). Both jobs passed: `pytest` and
  `docker build + /health`.
- **Live status of every run on this branch** (so this link cannot go stale):
  <https://github.com/eliaselkhoury/task-tracker-api/actions?query=branch%3Afinal-project>
- **Test command used by CI:** `pytest -vv`
- **Triggers:** `push` and `pull_request`, both unrestricted by branch.

### Shortcut check

| Shortcut | Present? | Evidence |
| -------- | -------- | -------- |
| `continue-on-error` | No | not in the file |
| `\|\| true` | No | not in the file |
| pytest skipped or conditional | No | the `Run the test suite` step has no `if:` |
| Vague Python version | No | `python-version: '3.12'`, matching the `Dockerfile` |
| Missing dependency install | No | `pip install -r requirements.txt`, and the job fails if it fails |
| Any `if:` that could hide a failure | One, and it cannot | `if: always()` on the `Container logs` step, so logs print *even when* an earlier step already failed. It guards a diagnostic step, never a verification one. |

Also hardened while I was in the file: `permissions: contents: read` (checkout
persists the token into `.git/config` by default, so a read-only token is the
cheap mitigation) and `timeout-minutes: 10` instead of GitHub's 6-hour default.

### The red run, and why it was red

Run #2 (<https://github.com/eliaselkhoury/task-tracker-api/actions/runs/31938756176>)
**failed**, and it is worth recording because the failure was real rather than
flaky. The `docker` job exited with **curl code 56 — "connection reset by peer"**.

`docker run -p 8000:8000` makes docker's userland proxy bind the host port
immediately, so during the second or two uvicorn takes to start, a connection is
*accepted and then reset* rather than refused. I had written
`--retry-connrefused`, which only adds `ECONNREFUSED` to curl's retry list — a
reset is not covered, so curl failed on the first attempt and never spent its
retry budget. Adding `--retry-all-errors` fixed it. HTTP status codes are still
not curl errors, so a `500` is not retried away: it reaches the assertion and
fails the job.

## Docker evidence

**Where this ran, and why.** The build and run were executed on `ubuntu-latest`
in GitHub Actions rather than on my machine. My machine is Windows 11 without
WSL2, and Docker Desktop's Linux engine cannot start without it — the client
installs and the named pipe appears, but every API call returns
`500 Internal Server Error ... check if the server supports the requested API
version`, and `wsl --install` needs administrator rights, a BIOS virtualisation
change and a reboot. The commands below are exactly what a teammate runs
locally; the log link is the proof they pass.

- **Build command:** `docker build -t task-tracker-api .`
- **Run command:** `docker run --rm -p 8000:8000 --name task-tracker task-tracker-api`
  (CI uses `-d` instead of `--rm` so later steps can exec into it)
- **`/health` check:** `200` with the exact expected body. The job asserts both,
  so a `404`, a `500` or a changed body fails the build:
  ```bash
  test "$code" = "200"
  test "$body" = '{"status":"ok","service":"task-tracker-api"}'
  ```
- **Non-root check:** implemented and asserted, not just claimed —
  `docker exec task-tracker id` and `test "$(docker exec task-tracker id -u)" != "0"`.
  The image creates `appuser` (uid 1000) and switches to it with `USER appuser`.
- **No-baked-secrets check:** asserted in the same step —
  ```bash
  test -z "$(docker run --rm task-tracker-api:ci \
             sh -c 'find /app -maxdepth 2 \( -name ".env*" -o -name ".git" -o -name "venv" \) -print')"
  ```
  `.dockerignore` keeps `.env`, `.env.*`, `data/`, `venv/`, `.venv/` and `.git/`
  out of the build context entirely, so there is nothing secret available to
  `COPY` even by mistake. The image also excludes `tests/`, `docs/`,
  `frontend/`, `scripts/` and `.vscode/` — it runs the API only.
- **Writability check:** the job POSTs a task to the running container, proving
  the non-root user can actually write `/app/data`. Only `/app/data` is chowned
  to `appuser`; the source stays root-owned and read-only to the runtime user.

## Documentation claim-vs-reality log

Every row was checked against the running app, the repo, or CI — not against
another document. Thirty API-level claims were checked with a script that
compares each README assertion to a live response; the rows below are the ones
worth reporting, including the four that were wrong.

| Claim checked | Evidence used | Result | Change made, if any |
| --- | --- | --- | --- |
| README API table: `201` create, `422` bad input, `404` unknown id, `409` illegal `todo→done`, `204` delete | 7 live requests against `127.0.0.1:8000`, status compared to the table | **Accurate** — 7/7 | none |
| "What `null` means in a PATCH": `description`/`assignee`/`due_date` clear with `200`; `title`/`status`/`priority` are `422` | 6 live PATCHes | **Accurate** — 6/6 | none |
| `GET /tasks` filters: `assignee` exact + case-insensitive, `q` substring over title *and* description, `overdue` tri-state, unknown enum `422`, no matches `200 []`, `q` over 200 chars `422` | 11 live requests | **Accurate** — 11/11. `?assignee=Mar` really does not match `Maria` | none |
| `is_overdue = due_date < today and status != done`; due *today* is not overdue; a `done` task never is; a past due date is accepted | 7 live requests covering every branch | **Accurate** — 7/7 | none |
| "`is_overdue` is derived on every read and never stored" | Read `data/tasks.json` off disk and checked every record for the key | **Accurate** — the key is absent from all stored records | none |
| "A rejected update writes **nothing** to `data/tasks.json`" | SHA-256 of the file, 6 malformed PATCHes (all `422`), SHA-256 again | **Accurate** — hash identical before and after | none |
| "The suite went from 20 to **91 tests**" | `pytest --collect-only -q` | **Accurate** — 5+25+2+23+13+23 = 91 | none |
| "Python 3.12+" | `python --version` → 3.12.10; `Dockerfile` and CI both pin 3.12 | **Accurate** | none |
| **AGENTS.md: "Python 3.11"** | Same check — the project runs 3.12 | **Wrong** | Corrected to 3.12, with the pins named |
| **AGENTS.md: "Status values are ToDo, InProgress, Done"** | `app/models.py` `TaskStatus` | **Wrong** — those are the frontend's display labels; the wire values are `todo`, `in_progress`, `done` | Corrected, with an explicit "do not 'fix' the API to match the labels" |
| **README: "byte-identical to the capture committed during the mid-course project"** | Ran the contract, diffed against all three committed captures | **Imprecise** — matches `contract-current.txt` only after stripping its UTF-8 BOM, and the two refactor captures differ by nine lines | Named the exact file, dropped "byte", explained the BOM |
| README: "The committed captures are byte-identical" (the two refactor captures) | `cmp docs/midcourse/contract-before-refactor.txt docs/midcourse/contract-after-refactor.txt` | **Accurate** — `cmp` reports no difference | none |
| **README Project layout block** | Compared every listed path against `git ls-files` | **Incomplete** — omitted `tests/test_update_null_fields.py`, and all the new release files | Added the missing test file, the three `docs/` files, `Dockerfile`, `.dockerignore`, `.github/workflows/ci.yml` and `AGENTS.md` |
| **`.env.example`: "relative to the project root"** | Set `DATA_FILE` and printed the resolved path | **Wrong** — a relative value resolves against the process working directory. It only *looks* right because the README tells you to run from the repo root | Comment rewritten to say so, and to point at absolute paths |
| CI: "pytest runs on push and pull request" | The `on:` block, plus run #1 firing on a push | **Accurate** — a null value for `on.push` is valid and means "all branches" | none |
| **CI: `pytest -v` produces verbose output** | Ran `pytest -v` and `pytest -vv` side by side | **Wrong** — `pytest.ini` sets `addopts = -q`, verbosity is a counter, so `-q -v` nets to 0 and the CI log printed dots, not test names | CI now runs `pytest -vv` |
| README/AGENTS.md Docker commands | Run verbatim by the CI `docker` job | **Accurate** — image builds, container answers `/health` with `200` | none |
| README: "the `mid-course-project` branch" | `git ls-remote --heads origin` | **Accurate** — the branch exists on the remote (`f0798c1`); it is simply not fetched locally | none (see the note in [final-ai-review.md](final-ai-review.md) — an AI reviewer called this a defect after checking only local refs) |

## Repository hygiene

- `git ls-files` lists **48** tracked files. No `.env`, no `data/`, no logs, no
  credentials, no personal or customer data.
- `data/tasks.json` is confirmed untracked via
  `git ls-files --error-unmatch data/tasks.json` (non-zero exit), and holds
  course demo data only.
- Nothing matching `.env` / `data/` / `*.log` / `secret` / `credential` /
  `token` was **ever** added in any commit on any branch, checked with
  `git log --all --diff-filter=A --name-only`.
- `.gitignore` now covers `.env.*` as well as `.env`. Verified with
  `git check-ignore -v` that `.env.local` and `.env.production` were previously
  **not** ignored.
