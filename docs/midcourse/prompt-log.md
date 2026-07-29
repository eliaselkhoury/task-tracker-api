# Prompt log

Prompts are summarised, not pasted verbatim in full. For each one: what I
asked, what came back, and what I did with it.

**Tools used:** Claude Code (Opus 5) in the terminal for most of the work,
GitHub Copilot inline suggestions in VS Code for repetitive markup and CSS.

---

## Weak prompt, rewritten

This is the one prompt I want on the record as a *before and after*, because the
rewrite is the reason the rest of the session went quickly.

### Weak version

> add due dates to the task tracker

**What came back:** a large single response that changed six files at once. It
added `due_date` as a `datetime`, added a validator rejecting any date in the
past, computed "overdue" in `app.js` with `new Date(task.due_date) < new Date()`,
added a `due_date` column to a *sort* control I had not asked for, and rewrote
`GET /tasks` to return `{"items": [...], "total": n}`.

**Why it was weak:** it named a feature, not a contract. No field type, no
definition of overdue, no statement about which layer owns the decision, no
mention of the existing tests, and no scope boundary — so the model filled every
one of those gaps with a guess, and four of the guesses were wrong for this app.

### Strong version

> Add an optional `due_date` to the Task Tracker. Constraints:
>
> - Type is `date`, not `datetime`. Serialised as `YYYY-MM-DD`.
> - Do **not** validate against today. A past due date must be accepted — that
>   is the case the feature exists to surface.
> - "Overdue" is decided in the **backend** and returned as a derived
>   `is_overdue` field on `TaskResponse`. Never stored in the JSON file.
> - Rule: `due_date is not None and due_date < today and status != done`.
>   Due *today* is not overdue.
> - Touch only `app/models.py`, `app/business_rules.py`, `app/storage.py`,
>   `app/main.py`. No sorting, no reminders, no response-shape changes —
>   `GET /tasks` keeps returning a plain array.
> - All 20 existing tests must still pass. Show me the diff before writing it.
>
> Explain where you put the overdue rule and why, before the code.

**What came back:** a plan naming `business_rules.is_task_overdue()` as the
home for the rule, then a diff confined to the four files. It matched the
constraints.

**What I did:** accepted the structure. Edited the docstring — its version said
"returns whether the task is late", mine spells out the three cases that are
*not* late, because those are the ones that get broken. Added the
`reference_date` parameter myself so tests could pin the boundary without
depending on the real clock.

---

## Feature 1 — Due dates + overdue filter

### F1-P1 — Where does "overdue" belong?

> The board needs an overdue badge on cards and an "overdue only" filter on
> `GET /tasks`. I could compute overdue in the backend and send a flag, or send
> `due_date` and compute it in JS. Argue both sides, then recommend one.
> Specifically address what happens when the browser's clock or timezone differs
> from the server's.

**Returned:** a fair comparison. For frontend: no extra field, no server work,
recomputes without a refetch. For backend: one source of truth. It initially
leaned frontend on the grounds of payload size, but when it worked through the
timezone question it reversed itself — the badge would use the browser's date
while the `?overdue=true` filter used the server's, so a card can be returned by
the filter and rendered without its badge.

**Accepted:** the backend recommendation, and the argument itself became
[decision 2](mini-adr.md) in the ADR.

**Rejected:** its follow-on suggestion to *also* send a server `today` field so
the frontend could compute overdue as a cross-check. Two mechanisms for one
answer is how they drift.

### F1-P2 — Boundary cases as a table

> For `is_task_overdue(due_date, status)`, list every boundary case as a table of
> input → expected output, including ones you think are obvious. Do not write
> code yet.

**Returned:** eleven rows. Nine matched what I wanted. Two I changed:

- It had `status=done, due_date=past → overdue=True`, reasoning that "it was
  delivered late, so it is late". Wrong for a board badge: the point of the pill
  is "this needs attention now". A finished task does not. Changed to `False`,
  and it is now `test_done_task_is_not_overdue_even_when_late`.
- It had `due_date == today → overdue=True`. The day is not over. Changed to
  `False`; it is now `test_task_due_today_is_not_overdue`, and Break Test 1
  showed this single boundary is what three tests hang off.

**Accepted:** the table as the test plan. Every row became a test in
`tests/test_due_dates.py`.

### F1-P3 — The tri-state filter

> Add an `overdue` query parameter to `GET /tasks`. It must be tri-state:
> absent = no filtering, `true` = overdue only, `false` = not-overdue only.
> `false` must include tasks with no due date. Reuse `is_overdue`; do not
> re-derive the rule in the query path.

**Returned:** `Optional[bool] = None` with a filter that reuses the derived
field. Correct, and the "reuse, do not re-derive" constraint is why there is
exactly one copy of the overdue rule in the codebase.

**Edited:** it named the parameter `is_overdue` to match the response field. I
renamed it to `overdue` — as a query parameter, `?overdue=true` reads as a
question about the list, while `?is_overdue=true` reads like it is setting a
field.

### F1-P4 — Reviewing the date rendering

> Review this card-rendering code for correctness, not style. It formats an
> API date string for display.

**Returned:** it caught its own earlier bug. The first version used
`new Date(task.due_date).toLocaleDateString()`, and `new Date("2026-08-04")` is
parsed as UTC midnight — which renders as **Aug 3** for anyone in a negative UTC
offset. Its fix splits the string and builds a local date from the parts.

**Accepted** the fix, and kept the explanation as the comment above
`formatDueDate`, because the code looks wrong without it and someone would
"simplify" it back.

---

## Feature 2 — Search + combined filters

### F2-P1 — Search scope, decided before coding

> Add a `q` search parameter to `GET /tasks`. Before writing code, tell me
> exactly which fields it searches and which it does not, and what happens for
> `q=""`, `q="   "`, and a 500-character `q`.

**Returned:** title + description; not id, timestamps, status, priority or
assignee. Empty and whitespace-only treated as no filter. It had no opinion on
length until asked, then suggested a cap.

**Accepted:** the scope, and each answer became a test —
`test_search_does_not_match_the_id_or_timestamps`,
`test_whitespace_only_search_is_treated_as_no_search`,
`test_overlong_search_string_returns_422`.

**Edited:** it suggested a 500-character cap. I used 200 via
`Query(max_length=200)` — the field it searches is capped at 120 and 1000, and
letting a query be longer than any title it could match is pointless.

### F2-P2 — Combining filters

> `GET /tasks` now takes `status`, `priority`, `assignee`, `overdue` and `q`.
> Write the filtering so all supplied filters combine with AND and any subset
> may be supplied. Keep `assignee` an exact case-insensitive match — it already
> is, and I do not want that widened.

**Returned:** correct AND semantics.

**Rejected:** despite the explicit constraint, the first draft still applied a
substring match to `assignee`, matching the `q` logic. I caught it reading the
diff, not from a test failure — the baseline had **no test** for the assignee
filter, so the suite would have passed. I kept the exact match and added
`test_list_tasks_filters_by_assignee` and
`test_assignee_filter_is_case_insensitive_but_still_exact`. This is the clearest
case in the project of review changing the result.

### F2-P3 — The refactor

> `storage.list_tasks` now has five near-identical
> `if x is not None: tasks = [t for t in tasks if ...]` blocks. Refactor to
> reduce the duplication. Behaviour must not change — I will diff a behaviour
> contract before and after. Flag anything in your version that could change
> behaviour.

**Returned:** the predicate list that is in the code now. It flagged the thing
worth flagging without being asked: lambdas that close over a reassigned local
all see the last value, so `needle` had to be bound per-predicate as a default
argument.

**Accepted:** the refactor and the warning. I turned the warning into Break
Test 2 to check it was a real risk rather than folklore — it was, and only 2 of
68 tests caught it. Both the comment in `storage.py` and
[decision 6](mini-adr.md) exist because of that.

### F2-P4 — Debouncing, scoped down

> Add a search box to the filter bar that queries the API as the user types,
> without firing a request per keystroke.

**Returned:** a debounce helper, plus an `AbortController` to cancel in-flight
requests, plus a loading spinner, plus caching of previous queries by key.

**Accepted:** the debounce helper (250 ms), applied to both free-text inputs.

**Rejected:** the other three. Against a local JSON file the responses come back
in single-digit milliseconds; a cache and a cancellation layer are state I would
have to keep correct for no measurable gain, and the existing status line
already covers loading. This is where I noticed the model optimises for the
impressive answer rather than the proportionate one, and that trimming its
output is part of the job.

---

## Prompt patterns that worked

1. **State the contract, not the feature.** Field types, the exact rule, the
   files it may touch, the response shape it may not change. `F1-P1` versus the
   weak prompt is the whole lesson.
2. **Ask for the decision before the code.** "Argue both sides, then
   recommend" and "explain where you put it and why" surfaced the timezone
   problem while it was still free to fix.
3. **Ask for boundary cases as a table, then turn the table into tests.** It is
   better at enumerating cases than at deciding them, so I took the enumeration
   and overruled two rows.
4. **Say what must keep working.** "All 20 existing tests must still pass" and
   "I will diff a behaviour contract" changed what it produced.
5. **Ask it to flag its own risks.** The closure warning in `F2-P3` came from
   asking, and it was the real bug.
6. **Assume every unstated decision will be guessed.** Four of the five things
   the weak prompt got wrong were things it was never told.
