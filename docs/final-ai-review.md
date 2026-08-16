# Final AI Review and Ownership Evidence

## How I ran the review

I used Claude Code (Opus 5) to run six read-only reviews of the release diff and repository. Each review focused on a different area: containers, CI, documentation, secrets, API surface, or supply-chain risk. A separate adversarial pass then attempted to refute the findings.

The release-diff review examined the changes from branch point `4d9547c` through release commit `9699b32`. Subsequent repository and security checks produced the fixes committed in `dae37b2`.

The reviewers returned 34 findings. I checked each finding against the repository before accepting, rejecting, or deferring it. The tables below record the findings that affected the submission or illustrate an important review decision. The exact reviewer count and review process are process attestations; Git records the resulting commits and Claude co-author trailers, but it cannot independently prove how many review passes were run.

## AGENTS.md checks

Commit `9699b32` created the first tracked `AGENTS.md` in this repository. It replaced earlier local guidance with repository-specific instructions covering:

- The correct stack and commands, including Python 3.12, FastAPI, Pydantic, uvicorn, pytest, and Docker.
- A read-first rule covering the README, ADR, and existing tests.
- A requirement to report documentation/code disagreements instead of silently resolving them.
- Restrictions on changes to `app/` and `frontend/`.
- The correct wire values for statuses and priorities.
- The requirement to validate a merged task before writing it.

Two factual errors from the earlier local guidance were corrected:

- Python was listed as 3.11 instead of 3.12.
- Task statuses used frontend labels rather than the API values `todo`, `in_progress`, and `done`.

Because the earlier guidance was not tracked, these two corrections are recorded in the `9699b32` commit message and are consistent with the current repository, but they are not visible as a before-and-after Git diff of `AGENTS.md`.

## Main review findings

| Finding | Grade | Decision |
| --- | --- | --- |
| `pytest -v` was cancelled out by pytest’s configured `-q` option. | **Useful** | Verified by running both verbosity levels. CI now uses `pytest -vv`. |
| Due-date tests used local dates while the application uses UTC. | **Useful** | Reproduced three failures during Beirut’s UTC-offset window. Both affected test files now derive their dates from UTC. |
| Python cache patterns in `.dockerignore` did not match nested directories. | **Useful** | Confirmed nested cache directories could enter the build context. Added the required `**/` prefixes. |
| CI jobs had no timeout. | **Useful** | Added `timeout-minutes: 10` to both jobs. |
| Docker execution and persistence needed to be documented. | **Useful** | The Docker section was added to `README.md` in the later review-fix commit `dae37b2`, including build, run, temporary-storage, and volume-mount instructions. |
| The `mid-course-project` branch did not exist. | **Wrong** | The reviewers checked only local references. `git ls-remote --heads origin` confirmed that the remote branch exists at `f0798c1`. |
| Six `.gitattributes` rules repeat the repository-wide LF policy, while the two CRLF exceptions currently match no tracked files. | **Noise** | Kept the explicit rules because they document intent and will apply when those file types are introduced. |
| Push and pull-request triggers can run CI twice for a pull-request commit. | **Noise** | Accepted deliberately because the jobs are short and the triggers can test different Git trees. |

## Security review

The following findings were valid and fixed:

- `task.id` and `task.priority` were inserted into `innerHTML` without escaping. They are now escaped as defence in depth.
- The Docker image gave the runtime user write access to all application source. Only `/app/data` is now owned by that user.
- The CI token inherited repository-default permissions. The workflow now declares `contents: read`.
- `.gitignore` ignored `.env` but not files such as `.env.local`. It now ignores `.env.*` while keeping `.env.example`.

I deliberately deferred three valid findings:

- The JSON store writes directly to the live file, so an interrupted or overlapping write could corrupt it.
- A corrupt or structurally invalid `tasks.json` produces an unclear server error.
- Seven direct requirements are pinned, while the reviewed environment contains 26 installed distributions and does not use a lockfile or hashes for the transitive dependency graph.

These are real limitations. Fixing the first two would change the main persistence path, while fixing the third requires a broader dependency-locking decision. I recorded them instead of making rushed changes before submission.

The CORS review was mechanically correct but did not justify a code change. The default allowlist is restrictive, and wildcard access only occurs if someone explicitly configures `*`. More importantly, CORS is browser behavior, not authentication: non-browser clients can still access this local, unauthenticated API.

No secrets, credentials, customer data, or runtime task data were found in the tracked repository contents or the historical diffs that were inspected. Normal Git metadata still contains contributor names and email addresses, so I do not claim that Git history contains no personal identifiers at all.

## Protected-directory change

The final-project branch contains one change under a protected directory:

**`frontend/app.js`:** `cardHtml()` now escapes `task.id` and `task.priority`.

The `app/` directory is unchanged from branch point `4d9547c`.

No JavaScript or DOM test harness exists in this project, so this defence-in-depth change did not receive an automated regression test. That is an explicit exception to the literal “every fix gets a failing test first” rule in `AGENTS.md`, not something I am claiming as full compliance.

The before-state is visible in the Git diff as raw interpolation into `innerHTML`. The after-state applies `escapeHtml`. I also performed browser verification to confirm that task cards rendered normally and that Edit actions still found the correct task. A future frontend test harness should add a malicious stored-ID rendering case.

## Manual verification

I independently checked three areas.

### 1. XSS reachability

The API does not allow a client to set a malicious task ID or invalid priority:

- Extra IDs supplied during creation are discarded and replaced with UUIDs.
- PATCH requests cannot change an ID.
- Invalid priority values return `422`.

A malicious ID could still enter through a manually edited JSON store because `TaskResponse.id` is an unconstrained string. I therefore kept the escaping change as defence in depth and confirmed in the browser that normal task cards and Edit actions still work.

### 2. Rejected updates

I hashed the task store, sent six invalid PATCH requests, and hashed it again. The file was unchanged, and `GET /tasks` still returned `200`.

The automated suite and behavior contract independently cover the same guarantee: rejected updates do not write to the store.

### 3. CORS behavior

With the default configuration:

- An allowed origin receives the appropriate allow-origin header.
- An unlisted origin receives no allow-origin header.
- A preflight request from an unlisted origin returns `400`.
- A non-browser client can still read the response body.

That behavior is acceptable for this local course project. The API would require authentication before public deployment.

## AI output I rejected or corrected

One reviewer claimed that the `mid-course-project` branch did not exist. Its adversarial verifier agreed because both checked only local references.

A remote check settled the question:

```text
f0798c15cf8027df67dbf3b534d1f29019963488 refs/heads/mid-course-project
```

I rejected the finding. This is a useful example because two AI passes reached the same answer and were still wrong: they had inspected the wrong Git scope.

I also corrected the Docker-documentation finding rather than rejecting it. Commit `9699b32` itself contained no Docker section in `README.md`; the documentation was added later in `dae37b2`. Describing the finding as wrong would contradict the commit history.

These examples are why I treat AI findings as leads rather than facts.

## My AI usage rules

1. Never provide AI tools with real credentials, tokens, environment values, production logs, customer data, or confidential information.
2. Verify every finding against the exact repository state it describes before changing anything.
3. Distinguish a commit from an uncommitted working tree.
4. Record AI contributions with a grade, explanation, and verification result.
5. Prefer an automated regression test; when no proportional harness exists, record the manual check and the limitation honestly.

## Ownership statement

I can explain every change in this branch, including code first suggested by AI.

The reviews helped identify issues I probably would have missed, especially the UTC/local-date mismatch and Docker ignore-pattern behavior. The Git history supports the resulting sequence: release infrastructure in `9699b32`, review-driven fixes in `dae37b2`, the CI health-probe correction in `ae01dd5`, and the review evidence in `8e6eddf`.

I reproduced accepted technical findings before acting on them and rejected the remote-branch finding after checking the remote directly. Where a finding was real but the fix would affect the main persistence layer without strong tests, I deferred it and documented the limitation.

The only protected-directory change was the defence-in-depth escape in `frontend/app.js`. It received manual browser verification but no automated DOM regression test, and that exception is recorded rather than hidden.

The AI expanded the review. It did not make the final decisions.
