# Mini-ADR — mid-course features

Status: **accepted**. Written before implementation, updated once during
Feature 2 (noted inline).

Two features were added to the Module 1–3 Task Tracker:

1. Due dates + overdue filter
2. Search + combined filters

They were chosen together because both extend the same endpoint (`GET /tasks`)
and the same modal, so the second feature reuses the first feature's plumbing
instead of opening a new front. Both are visible in the frontend.

---

## Decision 1 — `due_date` is a `date`, not a `datetime`

**Chosen:** `Optional[date]`, serialised as `YYYY-MM-DD`.

Users think of a due date as a day. A timestamp forces a decision about *which*
moment of the day the deadline is, and then about whose timezone that moment is
in — neither of which this app needs. `date` also makes the overdue comparison a
plain `due < today`.

**Rejected:** `datetime` (AI's first suggestion). It buys nothing here and
introduces timezone handling across storage, API, and the browser.

## Decision 2 — overdue is computed in the backend and exposed as `is_overdue`

**Chosen:** the API derives `is_overdue` on every task response.

```
is_overdue = due_date is not None
             and due_date < today
             and status != done
```

**Why:** the overdue *pill* and the `overdue=true` *filter* must never
disagree. If the badge is computed in JS from the browser clock and the filter
is computed in Python from the server clock, then near midnight — or with a
laptop in a different timezone — a card can be filtered in and rendered without
its badge. One source of truth removes the whole class of bug, and the frontend
gets simpler: it renders a boolean instead of doing date maths.

**Rejected:** computing it in the frontend (AI's suggestion, on the grounds
that it saves a field). The saved field is not worth two clocks.

**Rejected:** storing `is_overdue` in the JSON file. It is a function of the
current date, so a stored value is stale the moment the day changes. It is
derived on read.

## Decision 3 — a past due date is allowed

**Chosen:** no validation against today. Any parseable date is accepted on
create and update.

**Why:** you routinely enter work that was already due. Refusing it would make
the app unable to represent the exact situation the overdue feature exists to
highlight.

**Rejected:** the AI's `422 due_date must be in the future` validator.

## Decision 4 — `overdue` is a tri-state query parameter

**Chosen:** `Optional[bool]`. Absent = no filtering; `true` = overdue only;
`false` = not-overdue only (which includes tasks with no due date).

**Rejected:** a bare flag where only `overdue=true` is meaningful. Tri-state is
the same amount of code and answers "what is *not* late?" too.

## Decision 5 — `q` searches title and description; `assignee` stays exact

**Chosen:** `q` is a case-insensitive substring match over `title` and
`description`. `assignee` remains the case-insensitive **exact** match the
baseline already had.

**Why:** they answer different questions. `q` is "find me the card about auth".
`assignee` is "show me Maria's column". Making `assignee` fuzzy would have
silently changed a behaviour the baseline tests already pin down, and would make
`assignee=Ma` match both `Maria` and `Marc`.

**Rejected:** one fuzzy matcher applied to every text field (AI's suggestion).

**Rejected:** searching across *every* field including `id` and timestamps. It
makes results hard to explain — a search for `2026` matching everything created
this year is noise, not a feature.

## Decision 6 — all filters combine with AND, in one place

**Chosen:** a single `storage.list_tasks(...)` builds a list of predicates and
applies them in sequence. Routes only parse and pass through.

**Why:** filter combination is the part most likely to be got subtly wrong, and
having it in one function means one place to read and one place to test. It also
kept the route signature honest: the endpoint gained parameters, not logic.

**Note added during Feature 2:** the first working version had five sequential
`if filter is not None: records = [...]` blocks copy-pasted in
`list_tasks`. It worked and the tests passed, so I committed it as a checkpoint,
then refactored to the predicate list and re-ran the behaviour contract to
confirm nothing changed. See `verification.md`.

## Decision 7 — the frontend re-queries the API instead of filtering locally

**Chosen:** every filter change builds a query string and calls `GET /tasks`.

**Why:** the backend is where the filter rules live, so asking it means the UI
cannot drift from the API. It also keeps the client honest about overdue, which
it deliberately cannot compute (Decision 2).

**Cost accepted:** a request per filter change. Mitigated by debouncing the
search box (250 ms) so typing does not fire a request per keystroke.

**Rejected:** fetching all tasks once and filtering in JS. Faster to type
against, but it duplicates every rule from Decision 5 in a second language.

## Decision 8 — `GET /tasks` still returns a plain array

**Chosen:** unchanged response shape.

**Rejected:** `{"items": [...], "filters": {...}, "total": n}` (AI's
suggestion). It is a breaking change to the contract that the frontend and all
20 baseline tests depend on, and every value in the envelope is something the
caller already knows or can count. The match count the UI shows is
`tasks.length`.

## Explicitly out of scope

Kept out to stay inside the "small enough to finish and explain" bar:

- **Saved views / filter presets.** Needs persistence and a settings surface;
  not central to Modules 1–3.
- **Recurring due dates.** Suggested by the AI. Would need a recurrence rule
  model and a scheduler — a whole feature on its own.
- **Email or push reminders for overdue tasks.** Needs a background job and an
  outbound integration.
- **Sorting the board by due date.** Would have been cheap, but it is a third
  feature. The board keeps insertion order.
- **Server-side pagination.** The JSON store holds tens of tasks, not
  thousands. Adding it now would be speculative.
- **Full-text indexing / relevance ranking.** A substring scan over a small
  JSON file is the right tool at this size.
