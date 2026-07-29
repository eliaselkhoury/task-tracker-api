# User stories

Two features, drafted with AI help before any code was written, then reviewed
and corrected. Each story has acceptance criteria. The **AI assumption I
corrected** notes at the end of each feature are the assumptions the model made
that I did not accept.

---

## Feature 1 — Due dates + overdue filter

### F1-S1 — Set a due date when creating a task

> As someone planning work, I want to give a task a due date when I create it,
> so the board shows when it needs to be finished.

**Acceptance criteria**

- The New Task modal has a **Due date** field, and it is optional.
- Saving with a date in `YYYY-MM-DD` returns `201` and the stored task carries
  that `due_date`.
- Saving with the field left blank returns `201` and `due_date` is `null` —
  a blank field is not an error.
- A malformed date (`31/12/2026`, `not-a-date`, `2026-13-45`) returns `422`
  and the modal shows the error without closing or losing typed input.

### F1-S2 — See the due date on the card

> As someone scanning the board, I want each card to show its due date, so I
> can judge urgency without opening anything.

**Acceptance criteria**

- A task with a due date shows a date pill on its card.
- A task without one shows no date pill at all (not "no due date").
- The date is shown in a readable form (e.g. `Aug 4`), not a raw ISO string.

### F1-S3 — Spot overdue tasks immediately

> As someone reviewing progress, I want overdue tasks to stand out, so nothing
> silently slips.

**Acceptance criteria**

- A task is overdue when it has a due date, that date is **before today**, and
  its status is not `done`.
- A task due **today** is not overdue.
- A `done` task with a past due date is **not** overdue.
- An overdue card shows a red **Overdue** pill.
- `is_overdue` is present on every task in the API response, so the badge and
  the filter can never disagree.

### F1-S4 — Filter the board down to overdue work

> As someone triaging, I want to hide everything that is not overdue, so I can
> deal with the backlog first.

**Acceptance criteria**

- `GET /tasks?overdue=true` returns only overdue tasks.
- `GET /tasks?overdue=false` returns only tasks that are *not* overdue,
  including tasks with no due date at all.
- Omitting the parameter returns everything.
- The UI has an **Overdue only** control; toggling it re-queries the API rather
  than filtering the copy already in the browser.
- All three columns stay visible when the filter empties some of them.

### F1-S5 — Change or clear a due date

> As someone re-planning, I want to move a due date or remove it entirely.

**Acceptance criteria**

- `PATCH` with a new `due_date` updates it and returns `200`.
- `PATCH` with `"due_date": null` clears it.
- A `PATCH` that does not mention `due_date` leaves the existing value alone.
- Clearing an overdue task's due date makes `is_overdue` false.

### AI assumptions I corrected — Feature 1

1. **It wanted to reject past due dates on create.** The first draft added a
   validator raising `422` for any date before today. That is wrong for this
   app: you often enter a task that was already due last week, and it should
   land on the board *as overdue*, not be refused. I removed the validator and
   wrote `test_create_task_accepts_a_past_due_date` to lock the behaviour in.
2. **It proposed `datetime` for `due_date` and computing overdue in the
   frontend.** Two problems. A full timestamp invites timezone bugs for a field
   users think of as a day, so I used `date`. And computing overdue in JS means
   the badge uses the browser's clock while the `overdue=true` filter uses the
   server's — they can disagree across midnight or across timezones. I made the
   backend the single source of truth and exposed `is_overdue` on the response.

---

## Feature 2 — Search + combined filters

### F2-S1 — Search by text

> As someone with a full board, I want to type a word and see only matching
> tasks, so I can find one without reading every card.

**Acceptance criteria**

- `GET /tasks?q=auth` matches against **title and description**.
- Matching is case-insensitive and matches partial words (`aut` finds `auth`).
- A `q` of only whitespace is treated as no search at all, not as a search for
  a space.
- No matches returns `200` with `[]` — never `404`.

### F2-S2 — Combine filters

> As someone triaging, I want to combine search with status, priority,
> assignee and overdue, so I can ask a precise question.

**Acceptance criteria**

- All supplied filters combine with **AND**.
- Any subset may be supplied; omitted filters are ignored.
- `q=redesign&priority=high&status=in_progress` returns only tasks matching all
  three.
- An unknown value for an enum filter (e.g. `priority=urgent`) returns `422`.

### F2-S3 — Drive it from a filter bar

> As a board user, I want one compact bar above the board for search and
> filters, so I do not need to know about URLs.

**Acceptance criteria**

- A bar above the board holds: search box, status, priority, assignee, and the
  **Overdue only** toggle from Feature 1.
- Typing in the search box is debounced so one keystroke is not one request.
- The three columns remain visible while filtered, each showing its own empty
  state when it has no matches.
- A **Clear** button resets every control and reloads the full board.

### F2-S4 — Understand what I am looking at

> As a board user, I want to know that a filter is active and how much it hid,
> so an empty board is never confusing.

**Acceptance criteria**

- While a filter is active, the status line reports the match count.
- If a filter matches nothing, the message says so explicitly and points at the
  Clear button, instead of leaving three silently empty columns.
- Editing a task while filters are active re-applies the same filters
  afterwards, rather than resetting the view.

### F2-S5 — Keep filtering honest about status

> As a board user, I want the status filter to narrow the board without
> breaking the Kanban layout.

**Acceptance criteria**

- Choosing `status=done` leaves ToDo and In Progress rendered but empty.
- Column counts reflect the **filtered** result, not the whole store.
- Drag-and-drop still works on a filtered board, and a card that no longer
  matches the active filter after a move disappears on refresh.

### AI assumptions I corrected — Feature 2

1. **It wanted `assignee` search to be a partial, fuzzy match.** The suggested
   code applied the same "substring, case-insensitive" rule to `assignee` as to
   `q`. But `assignee` was already an **exact** (case-insensitive) filter in the
   Module 2 baseline, so accepting that draft would have silently changed
   existing behaviour — and `assignee=Mar` would then match both `Maria` and
   `Marc`. I kept `assignee` exact, let `q` be the fuzzy one, and noticed while
   reviewing that the baseline pinned this behaviour in code but had **no test**
   for it. I added `test_list_tasks_filters_by_assignee` and
   `test_assignee_filter_is_case_insensitive_but_still_exact` so the next
   refactor cannot widen it by accident.
2. **It wanted to add a `filters` object to the response body.** The draft
   changed `GET /tasks` from returning a JSON array to returning
   `{"items": [...], "filters": {...}}`. That is a breaking change to the
   contract the frontend and all 20 baseline tests rely on, in exchange for
   information the client already has. Rejected; `GET /tasks` still returns a
   plain array.
