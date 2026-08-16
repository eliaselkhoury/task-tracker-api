# My AI Playbook

Written after finishing the Task Tracker. Every rule here comes from something
that actually happened on this project, not from a policy document.

Tools I used: **Claude Code (Opus 5)** in the terminal for most of the work,
**GitHub Copilot** inline in VS Code for repetitive markup and CSS.

## When I reach for AI first

- **Arguing a decision before I write any code.** "Compute overdue in the
  backend or the frontend? Argue both sides, then recommend." That prompt is the
  reason `is_overdue` is server-derived: it worked through the timezone case and
  reversed its own recommendation. I would have written the cheap JS version.
- **Enumerating boundary cases as a table.** It is much better at listing cases
  than at deciding them. I asked for every input→output row for
  `is_task_overdue`, got eleven, overruled two, and turned the table into
  `tests/test_due_dates.py`.
- **Behaviour-preserving refactors I can prove.** Five near-identical filter
  blocks became a predicate list, and I diffed a behaviour-contract capture
  before and after to prove nothing moved.
- **Boilerplate I have already established the pattern for** — another filter
  input, another pill variant, another parametrised list of bad dates. This is
  Copilot's job, and it is a poor place to decide anything.
- **Config and packaging in languages I write once a year** — the Dockerfile,
  the CI YAML. High syntax cost, low judgement cost, and CI tells me
  immediately whether I was wrong.
- **A second opinion on a diff I already understand.** Not to find out what the
  diff does — to find out what I missed.

## When I do not reach for AI first

- **When I cannot yet state the contract.** The prompt "add due dates to the
  task tracker" cost me more time than writing it myself: it invented a sort
  control, changed `GET /tasks` to return an envelope, and added a validator
  refusing past due dates — which would have made the app unable to represent
  the exact situation the feature exists to surface. If I cannot name the field
  type, the rule, and the files it may touch, I am not ready to ask.
- **When the answer has to be true rather than plausible.** Versions, CVEs,
  whether a specific pinned release is affected. I check those against the
  actual file or the actual advisory. In this final project a reviewer told me a
  workflow trigger behaved a certain way; I only recorded it after I had
  confirmed it myself.
- **When the thing I am debugging is my own mental model.** The `--reload`
  incident on this project — the server silently stopped watching for changes
  and served stale code while pytest passed against the new code — was not a
  code bug at all. No amount of asking about the code would have found it.
  Reproducing it by hand did.
- **When it is a decision only I can own** — scope, what to cut, what "done"
  means. AI optimises for the impressive answer, not the proportionate one.
- **When I am supposed to be learning the thing.** If I let it write the part I
  do not understand, I will not understand it next week either.

## My non-negotiables

1. **No real secrets or personal data, ever** — not in the repo, not in a
   prompt, not in a commit message. `.env` and `data/` are gitignored and
   excluded from the Docker build context so it is enforced, not remembered.
   I verify with `git ls-files`, not by trusting `.gitignore`.
2. **I do not submit a line I cannot explain.** If I cannot say why it is there,
   it comes out — regardless of whether it works.
3. **Nothing merges on a green suite alone.** A green suite only means the code
   passes the tests I thought to write. Break Test 2 on this project left
   **66 of 68 tests passing with a real bug present**.
4. **AI does not get to change scope.** New endpoints, auth, a database, a UI
   refresh — if I did not ask for it, it does not go in, however good it is.
5. **AI contributions get recorded** — what I accepted, what I edited, what I
   rejected and why. This file and `docs/final-ai-review.md` are that record.

## My review rules

- **Read the diff, not the summary.** The clearest case on this project: I said
  twice to keep `assignee` an exact match, and the diff made it a substring
  match anyway to mirror the new `q` logic. I caught it reading the diff. There
  was no test for the assignee filter, so the suite would have gone green and
  `assignee=Mar` would quietly have matched both Maria and Marc.
- **Ask what the tests do not cover, then write that test.** Every bug I have
  actually shipped on this project lived in the gap between "passes" and
  "correct".
- **Run the command, do not trust the claim.** For the release check I hashed
  `data/tasks.json`, fired six malformed PATCH requests, and re-hashed it. That
  is worth more than the README paragraph asserting the same thing.
- **Grade findings; do not just collect them.** Valid, false positive, or noise,
  with a reason. A review that reports everything is a review I will stop
  reading.
- **Make it show its work on risk.** "Flag anything in your version that could
  change behaviour" produced the closure warning that turned out to be the real
  bug. Asking is what surfaced it.
- **When the docs and the code disagree, that disagreement is the finding.**
  Do not quietly pick one. `AGENTS.md` claimed Python 3.11 and listed the
  frontend's display labels as the API's status values; both were wrong, and
  finding them mattered more than fixing them.

## What I am still figuring out

- **How much context to hand over.** Too little and it guesses; too much and it
  optimises for the wrong thing. `AGENTS.md` is my current answer and I do not
  know yet whether it is the right size.
- **Where the line is between hardening and scope creep.** I found an unescaped
  interpolation in the frontend that I proved is not reachable through the API.
  Fixing it is one line; not fixing it respects the scope rule. I argued myself
  onto one side of that (see `docs/final-ai-review.md`) and I am still not sure
  it generalises.
- **Whether pinned-but-unhashed dependencies are good enough** for a project
  this size, or whether a lockfile is the honest minimum.
- **Team norms.** Everything here is a habit of mine, enforced by me. I do not
  know which of these survive contact with a team that does not share them, or
  how to ask a reviewer to grade my AI usage rather than only my code.

## Decision Card

| Situation | What I do |
| --------- | --------- |
| **New feature** | Write the contract first — field types, the exact rule, the files it may touch, the response shape it may not change, the tests that must still pass. Ask for the decision and the diff *before* the code. No contract, no prompt. |
| **Code review** | AI reviews the diff, I grade every comment Useful / Noise / Wrong with a reason, and I re-derive anything I intend to act on from the actual file. Its job is to widen the search, not to reach the verdict. |
| **Debugging** | Reproduce it by hand first. Give AI the real error, the real input and the failing test — never a paraphrase. If it proposes a fix, the fix needs a test that fails before it. |
| **Infrastructure** | Let it draft the YAML and the Dockerfile, then read every line and run it for real. Green CI and a `200` from `/health` in a container are the acceptance criteria, not "it looks right". |
| **Never paste** | Real credentials, tokens, `.env` values, production logs, customer or personal data, anything under NDA. Placeholders only. |
| **My one rule** | **If I cannot explain it, it does not ship** — no matter how well it works or how confident the model sounded. |
