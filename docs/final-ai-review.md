# Final AI Review and Ownership Evidence

**How this review was run.** A read-only review with Claude Code (Opus 5): six
reviewers over the release diff and the repo, each given a different lens
(container, CI, docs-vs-reality, secrets, API surface, supply chain), and each
finding then handed to a separate adversarial verifier told to *refute* it and
to default to the harsher grade. 34 findings came back. The grades below are
mine: I re-derived every finding I acted on against the actual file, and the two
graded **Wrong** are ones where the reviewer — and in one case the verifier too —
was confidently incorrect.

The diff reviewed is commit `9699b32`, which added `.github/workflows/ci.yml`,
`Dockerfile`, `.dockerignore`, `.gitattributes` and rewrote `AGENTS.md`.

## AGENTS.md guardrails

- Repo-specific stack and commands included: **yes** — pinned versions for
  Python, FastAPI, Pydantic, uvicorn and pytest, plus the run, test, contract
  and Docker commands.
- Docs-first/read-first guardrail included: **yes** — a "Read first, then write"
  section requiring the README, the mid-course ADR and the existing tests to be
  read before editing, and requiring a docs/code disagreement to be reported
  rather than silently resolved.
- Unexpected app/frontend edits rule included: **yes** — `app/` and `frontend/`
  may change only for a bug fix with a failing test, a security fix, or a
  documented correction, and every such change must be explained in this file.

Two errors in the previous `AGENTS.md` were found by the docs-vs-reality pass
and corrected: it claimed **Python 3.11** (the project runs 3.12) and listed the
status values as **"ToDo, InProgress, Done"**, which are the frontend's display
labels — the wire values are `todo`, `in_progress`, `done`. An agent following
that file would have "fixed" the API to match the labels.

## AI code review mini-log

| AI comment | Grade | Reason | Verification or decision |
| --- | --- | --- | --- |
| "`pytest -v` in CI is silently cancelled out by `addopts = -q` in pytest.ini" | **Useful** | Correct and non-obvious. pytest verbosity is a counter and ini `addopts` are prepended, so `-q -v` nets to 0. | Ran both: `pytest -v` printed `.....  [5%]`, `pytest -vv` printed `test_todo_to_in_progress_is_allowed PASSED`. **Fixed** — CI now runs `pytest -vv`. |
| "Due-date tests compare the app's UTC 'today' against the machine's LOCAL today" | **Useful** — the best finding in the set | The app derives overdue from `utc_now().date()`; 14 test call sites built their dates from `date.today()`. In Beirut (UTC+3) those differ 00:00–03:00 local. A green CI badge was hiding it, because GitHub runners are UTC. | Reproduced by pinning the app's clock a day back: **exactly 3 failures** — `test_overdue_true_returns_only_overdue_tasks`, `test_overdue_false_includes_tasks_with_no_due_date`, `test_all_five_filters_at_once`. Swept all 24 hours: the old code disagreed with the server for **3/24** hours, the new code for **0/24**. **Fixed** in both test files. |
| "`__pycache__/` and `*.py[cod]` are root-anchored in .dockerignore, so nested caches under app/ are copied into the image" | **Useful** | I had copied these three patterns from `.gitignore` without knowing the two files anchor differently: git matches a slash-free pattern at any depth, Docker matches relative to the context root. Four nested cache dirs holding 10 `.pyc` files were being shipped. | Confirmed the anchoring rule and the four directories. **Fixed** with a `**/` prefix on the three Python-noise patterns only — the rest (`data/`, `venv/`, `tests/`) sit at the root, where root-anchoring is correct. |
| "The job has no `timeout-minutes`, so a hung test blocks on GitHub's 6-hour default" | **Useful**, minor | True, cheap, and a real cost if it ever fires. | **Fixed** — `timeout-minutes: 10` on both jobs. |
| "The task store is ephemeral and Docker is undocumented — I confirmed `grep -i docker README.md` returns nothing" | **Wrong** | The load-bearing evidence is fabricated. That grep returns **six** hits. The README has a section titled "How to run with Docker" that already gives the build command, the run command, the fact that tasks vanish with `--rm`, and the exact `-v "${PWD}/data:/app/data"` mount the finding says is missing. | Ran the grep myself. **Rejected.** See "One AI output I rejected" below. |
| "README points at a `mid-course-project` branch that does not exist in this repo" | **Wrong** | The branch exists. Both the reviewer and its adversarial verifier checked only *local* refs — `git for-each-ref` and `git branch --all` — and neither ran `git ls-remote`. | `git ls-remote --heads origin` returns `f0798c1 refs/heads/mid-course-project`. The remote-tracking ref simply was never fetched locally. **No change made.** |
| "Six of the nine `.gitattributes` rules are no-ops; the two that aren't match zero tracked files" | **Noise** | Factually true and consequence-free. The rules exist for files that do not exist *yet* — a `.sh` or a `.bat` added later is exactly when the normalisation matters. | Kept as written. Documented intent is worth more than the two lines it costs. |
| "push + pull_request with no `concurrency:` block runs the suite twice per PR commit" | **Noise** | True. The jobs take 12s and 18s, and I want both triggers: push covers direct pushes, pull_request covers the merge commit, which is a different tree. | Accepted the duplication deliberately. |

## AI security mini-review

| Finding | File evidence | Grade | Reason | Next action |
| --- | --- | --- | --- | --- |
| `task.id` and `task.priority` are interpolated into `innerHTML` without `escapeHtml`, unlike title/description/assignee | `frontend/app.js:194` in the reviewed commit `9699b32` — `cardHtml()`, now at `:200-221` | **Valid** | The sink is real even though no reachable path exists today. `TaskResponse.id` is an unconstrained `str`, so a hand-edited `data/tasks.json` reaches it. | **Fixed** as defence in depth — a no-op for a uuid and an enum member. Explained in full below. |
| `chown -R appuser:appuser /app` gives the runtime user write access to its own source | `Dockerfile:39` in `9699b32`, now `:45` | **Valid** | Low severity — there is no code-execution path in `app/` today — but it weakens a property the Dockerfile explicitly claims for itself, and any future file-write bug would become persistence across a restart. | **Fixed** — only `/app/data` is chowned. Source stays root-owned and world-readable, which is all the app needs to import it. |
| The CI job declares no `permissions:`, so `GITHUB_TOKEN` inherits the repository default | `.github/workflows/ci.yml` | **Valid** | The route is real but not the one first described: `actions/checkout` defaults to `persist-credentials: true`, writing the token into `.git/config`, where any later step in the job can read it — including setup code run by `pip install` from 19 unpinned transitive packages. | **Fixed** — `permissions: contents: read`. |
| `.gitignore` ignores `.env` but not `.env.local` / `.env.production`, while `.dockerignore` covers both | `.gitignore:13` | **Valid** | A verified inconsistency between two guardrails I wrote deliberately, in a repo that pushes to a public remote. Exposure needs a human action (`cp .env .env.backup`), and the reviewer said so rather than inflating it. | **Fixed** — `.env.*` with `!.env.example`. Confirmed with `git check-ignore -v` that `.env.local` and `.env.production` were genuinely not ignored before. |
| `_write_all` truncates the live JSON file in place — an interrupted or overlapping write destroys the whole store | `app/storage.py:60-65` | **Valid**, deliberately **not** fixed | Mechanically correct: `open("w")` truncates before any bytes are written, there is no temp+rename and no lock, and route handlers are sync `def` so Starlette really does run two at once. | **Deferred, with reasons.** The fix (write to a temp file, `os.replace`) is small, but it changes the write path of the only persistence layer, and I cannot write a test that proves a crash mid-write — so I would be shipping an untested change to `app/` days before submission to fix a failure I have not observed. Recorded here as a known limitation instead. |
| A corrupt or non-list `tasks.json` turns every endpoint into an opaque `500`, and `[1,2,3]` gets re-persisted | `app/storage.py:48-57` | **Valid**, deliberately **not** fixed | All four corruption shapes were re-derived independently and are correct. | **Deferred.** A `try/except` in `_read_all` is easy, but choosing the right status code for "the server's own store is broken" across all five routes is a design decision, not a patch, and `app/` is protected. Named here so the next maintainer has it. |
| Only 7 of the 26 installed packages are pinned; 19 float at install time | `requirements.txt` | **Valid** | Verified by counting `dist-info` directories against the file. This bites without an attacker: a fresh CI install can resolve a different tree than my venv, so local-green/CI-red can differ by a package nobody edited. | **Recorded, not fixed.** A lockfile or hash pinning is the real answer and is beyond the scope of a no-new-features release. Listed in the playbook as an open question. |
| A single `*` anywhere in `CORS_ORIGINS` silently disables the whole allowlist on an API with no authentication | `app/main.py:29-35` | **Noise** | Every mechanical claim is true — Starlette's check is literally `"*" in allow_origins` — but nothing triggers it. The shipped default is the two Live Server origins, there is no `.env`, and writing `*` is an explicit "let everything in" instruction, not a slip. The proposed `raise ValueError` would break a student who sets `*` on purpose. | No code change. The verification itself is worth keeping: default allowlist confirmed restrictive, `allow_credentials=False` hardcoded and not environment-driven. |
| No secrets, credentials or personal data anywhere in the working tree or git history | `git ls-files`, `git log --all` | **Valid** (clean result) | The most important finding is the negative one, and it was produced by commands rather than by reading `.gitignore`. | Nothing to do. Recorded in [release-evidence.md](release-evidence.md#repository-hygiene). |

### Changes made to a protected directory

One, required to be declared here by the rule in `AGENTS.md`:

**`frontend/app.js` — `cardHtml()` now escapes `task.id` and `task.priority`.**
`app/` is untouched.

## Manual security check

Three checks I ran myself, before and independently of the AI review. None is a
restatement of an AI finding, and the third contradicts one.

**1. Is the unescaped `innerHTML` sink actually reachable?** I found the
unescaped `${task.id}` / `${task.priority}` by reading `cardHtml()`, then tried
to exploit it rather than assuming either way:

- `POST /tasks` with `{"title":"xss probe","priority":"high","id":"\" onmouseover=\"alert(1)"}`
  → the server returned `id = 1d0fd077-0604-465f-9889-5875927925d9`. The extra
  key is dropped by `TaskCreate` and `storage.add_task` overwrites it with
  `str(uuid.uuid4())`.
- `PATCH` with an `id` key → accepted, and re-reading the task shows the id
  **unchanged**.
- `POST` with `"priority": "<img src=x>"` → `422`.
- But `TaskResponse.model_validate({"id": '" onmouseover="alert(1)', ...})`
  **succeeds** — `id: str` has no format constraint
  (`TaskResponse.model_fields["id"].metadata` is empty).

So: not reachable through the API, reachable through a hand-edited store. I
escaped it anyway and said exactly why in the code comment. Then I verified in
the browser that the change did not break the read-back: all seven cards'
`data-id` values are still clean uuids, every Edit button's `data-id` matches
its card, and clicking Edit on "Renew SSL certificate" opens the modal populated
with that task's real title, priority, assignee and due date — which exercises
the same `tasks.find(t => t.id === button.dataset.id)` lookup the save path uses.

**2. Does a rejected request really leave the store untouched?** The README
claims "a rejected update writes **nothing**". I tested it instead of trusting
it: SHA-256 the file, fire six malformed PATCHes (`title:null`, `status:null`,
`priority:null`, blank title, bogus status, 500-character title — all `422`),
SHA-256 again. **Identical hash, identical byte count**, and `GET /tasks` still
returns 200. The claim holds under test.

**3. Is CORS doing what I think it is?** With the default allowlist:

- `Origin: http://127.0.0.1:5500` → `200`, `access-control-allow-origin: http://127.0.0.1:5500`
- `Origin: https://evil.example` → `200`, and **no** `access-control-allow-origin` header
- Preflight `OPTIONS` from `https://evil.example` → `400 Disallowed CORS origin`

The part worth writing down is the second line. The unlisted origin still gets a
`200` **with the full task list in the body** — the browser is what discards it.
CORS is not access control, and this API has no authentication, so anything that
is not a browser (`curl`, a script) can read and write everything. That is
acceptable for a local single-user course project and unacceptable the moment it
is deployed, and I would rather state it than let a green CORS check imply a
protection that does not exist.

## One AI output I rejected or corrected

The container reviewer returned a **high-confidence** finding that the task
store is ephemeral and that this is undocumented, with what looked like real
evidence: *"I confirmed there is no Docker documentation anywhere: `grep -i
docker README.md` returns nothing."* It recommended I document the run command
in "the README's pending Final Project section".

I ran the grep. It returns **six** hits. The Final Project section was not
pending — it was already written, already titled "How to run with Docker", and
already contained the build command, the run command, the sentence *"Tasks
created inside the container live in the container and disappear with `--rm`"*,
and the exact `-v "${PWD}/data:/app/data"` mount the finding claimed was
missing. The reviewer had asserted the result of a command it did not run, and
then built a two-part failure scenario on top of it.

**Rejected in full.** The rest of the finding — a UID-mismatch `PermissionError`
on Linux bind mounts — was also defused: the Dockerfile deliberately pins
`--uid 1000`, which matches the default first user on Debian and Ubuntu.

I kept the adversarial verifier's phrasing of why this matters, because it is
the right instinct: *fabricated supporting evidence on a high-confidence finding
is the strongest possible signal to reject it.*

A second one worth recording, because it shows the verification layer is not
infallible either: a finding claimed the README "points at a `mid-course-project`
branch that does not exist in this repo". The adversarial verifier **confirmed**
it, citing `git for-each-ref` and a failing `git checkout`. Both had only looked
at local refs. `git ls-remote --heads origin` shows
`f0798c1 refs/heads/mid-course-project` — the branch exists on the remote and
simply was never fetched into this clone. Two AI passes agreed, and both were
wrong; one extra command settled it.

## Three AI usage rules

1. **Never paste:** real credentials, tokens, `.env` values, production logs, or
   real personal or customer data — into a prompt, the repo, or a commit
   message. Placeholders only, and `.gitignore` plus `.dockerignore` enforce it
   so it does not depend on me remembering.
2. **Always verify:** run the command the finding is about before acting on it.
   Every fix in this document was re-derived against the actual file first, and
   doing that caught two confidently-wrong findings and one that understated its
   own blast radius by a whole test file.
3. **Record AI contributions by:** grading each one Useful / Noise / Wrong (or
   Valid / False Positive / Noise) with a reason and the verification that
   produced the grade — in this file, in `docs/ai-playbook.md`, and in commit
   messages that say what was changed and why rather than what was generated.

## Ownership statement

I can explain every line in this branch, including the ones I did not write
first. The AI reviews widened the search — the UTC-versus-local clock skew in
the test suite is a bug I would not have found on my own, and the `.dockerignore`
anchoring difference is a rule I did not know — but every finding was re-derived
against the real file before I acted on it, and the two that turned out to be
fabricated or wrong were rejected on evidence I gathered myself. Where a finding
was real but the fix would have meant an untested change to `app/`, I deferred it
and wrote down why, because shipping an unverifiable change to a protected
directory is worse than shipping a documented limitation. The claims in the
README are not assertions I inherited: 30 of them were checked against a running
server, and the four that were wrong or imprecise are corrected here and listed
in [release-evidence.md](release-evidence.md#documentation-claim-vs-reality-log).
The one change I made to a protected directory escapes the three `data-id`
interpolations and the `pill-` class interpolation in `cardHtml()` — a sink I
first proved was unreachable, kept anyway as defence in depth, and then verified
in the browser. If a grader asks me why `escapeHtml` is wrapped around a uuid, I
have a better answer than "the tool suggested it".
