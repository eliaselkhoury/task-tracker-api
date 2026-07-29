# Verification

Every command below was run on Windows 11, Python 3.12.10, inside the project
`venv`. Output is pasted as it appeared.

---

## 1. Baseline check (before any feature work)

Run before touching a line of feature code, on `main`, to establish that the
Module 1–3 app was green to start with.

```bash
pytest -v --no-header
```

```
============================= test session starts =============================
collected 20 items

tests\test_business_rules.py .....                                       [ 25%]
tests\test_health.py ..                                                  [ 35%]
tests\test_tasks_crud.py .............                                   [100%]

============================= 20 passed in 0.62s ==============================
```

The app was also started and opened before any changes, so the baseline was a
running app and not just a green suite:

```
GET http://127.0.0.1:8000/health -> {"status":"ok","service":"task-tracker-api"}
GET http://127.0.0.1:5500/index.html -> 200
```

Board rendered four seeded tasks across all three columns, browser console
clean (no errors, no warnings).

**Baseline: 20 passed, app runs, frontend renders.**

---

## 2. Backend test results (after both features)

```bash
pytest
```

```
....................................................................     [100%]
68 passed in 3.94s
```

Per file:

| File                            | Tests | Origin              |
| ------------------------------- | ----: | ------------------- |
| `tests/test_health.py`          |     2 | baseline            |
| `tests/test_tasks_crud.py`      |    13 | baseline            |
| `tests/test_business_rules.py`  |     5 | baseline            |
| `tests/test_due_dates.py`       |    25 | **new — Feature 1** |
| `tests/test_search_filters.py`  |    23 | **new — Feature 2** |
| **Total**                       | **68** | 20 baseline + 48 new |

The brief asks for at least 4 new tests. There are 48. They are not padding —
Break Test 2 below shows that 66 of the 68 pass while a real bug is present, and
only the combined-filter tests catch it.

---

## 3. Manual browser checks

Backend on `127.0.0.1:8000`, frontend served on `127.0.0.1:5500`. Each row was
checked in the browser with the network log and console open. "Request seen" is
copied from the network log — it is how I confirmed the UI queries the API
rather than filtering a local copy.

### Feature 1 — due dates and overdue

| # | Check | Request seen | Result |
| - | ----- | ------------ | ------ |
| 1.1 | Card with a future due date | `GET /tasks` | Neutral pill `Due Aug 3` ✅ |
| 1.2 | Card with a past due date, status `todo` | `GET /tasks` | Red pill `Overdue · Jul 26`, red card border ✅ |
| 1.3 | Card due **today** | `GET /tasks` | Neutral pill `Due Jul 29`, **not** flagged overdue ✅ |
| 1.4 | Card past due but status `done` | `GET /tasks` | Neutral pill `Due Jul 26`, **not** flagged overdue ✅ |
| 1.5 | Card with no due date | `GET /tasks` | No date pill at all ✅ |
| 1.6 | Tick "Overdue only" | `GET /tasks?overdue=true` | 1 card; status line `1 matching task(s).` ✅ |
| 1.7 | All three columns while filtered | — | `todo`, `in_progress`, `done` all rendered; 2 show `Nothing here yet.` ✅ |
| 1.8 | Create a task with a **past** due date via the modal | `POST /tasks` → 201 | Accepted, toast `Task created.`, rendered `Overdue · Jul 20` ✅ |

Checks 1.3 and 1.4 are the two boundaries the AI originally got wrong, verified
in the real UI and not only in pytest.

### Feature 2 — search and combined filters

| # | Check | Request seen | Result |
| - | ----- | ------------ | ------ |
| 2.1 | Type `sign` in search | `GET /tasks?q=sign` | 2 cards (one title match `rede**sign**`, one description match) ✅ |
| 2.2 | Add Priority = High to that search | `GET /tasks?q=sign&priority=high` | 1 card — AND, not OR ✅ |
| 2.3 | Columns while filtered to 1 result | — | All 3 columns rendered, 2 empty states ✅ |
| 2.4 | Search `kubernetes` (no matches) | `GET /tasks?q=kubernetes` | 0 cards, 3 columns still rendered, status line `No tasks match the current filters. Use "Clear" to see them all.` ✅ |
| 2.5 | Click **Clear** | `GET /tasks` | All five controls reset, full board back, status line empty ✅ |
| 2.6 | Debounce on typing | — | One request after typing stops, not one per keystroke ✅ |

### Failure states

| # | Check | Result |
| - | ----- | ------ |
| 3.1 | Edit a `todo` task to `done` in the modal | `PATCH` → **409**. Modal stays **open**, shows `cannot move a task from 'todo' to 'done'; allowed next values are: in_progress, todo`, and the typed title is preserved ✅ |
| 3.2 | Backend stopped, reload the page | Status line shows `Cannot reach the API. Is the backend running on http://127.0.0.1:8000 ?`, styled as an error, and the 3 columns still render — the board does not just sit silently empty ✅ |
| 3.3 | Console across all checks | No errors, no warnings ✅ |

### Two notes on honest reporting

- Malformed due dates (`31/12/2026`, `soon`) **cannot** be entered through the
  UI — `<input type="date">` refuses them before a request is made. The `422`
  path is therefore covered by pytest
  (`test_create_task_rejects_malformed_due_date`, 5 parametrised cases) and by
  the behaviour contract, not by a browser check. I am not claiming a manual
  check I did not perform.
- Two throwaway tasks titled `Test` exist in my local `data/tasks.json` from
  clicking around the UI. `data/` is gitignored, so they are not in the repo,
  but they are visible in some counts above (6 cards rather than 4).

---

## 4. Behaviour contract, before and after the refactor

The refactor: `storage.list_tasks` had five copy-pasted
`if x is not None: tasks = [t for t in tasks if ...]` blocks. They became one
predicate list applied with `all()` over a single pass of the store.

`scripts/behavior_contract.py` drives the API through a fixed script — 4 seeded
tasks, 5 validation cases, 4 status transitions, 4 due-date updates, 3 not-found
cases, and **21 list queries** covering both features and their combinations —
and prints every status code and result. All dates are relative to today, so the
output is stable on any day it is run.

```bash
# on the working checkpoint, before refactoring
python scripts/behavior_contract.py > docs/midcourse/contract-before-refactor.txt

# after refactoring
python scripts/behavior_contract.py > docs/midcourse/contract-after-refactor.txt

# compare
Compare-Object (Get-Content docs/midcourse/contract-before-refactor.txt) `
               (Get-Content docs/midcourse/contract-after-refactor.txt)
```

```
contract IDENTICAL after restore
```

Both captures are committed, so the claim is checkable rather than asserted.
`pytest` also stayed at **68 passed** across the refactor.

Selected lines from the contract, which double as a readable statement of what
the two features do:

```
--- validation on create ---
POST /tasks [blank title] -> 422
POST /tasks [unknown priority] -> 422
POST /tasks [malformed due_date] -> 422
POST /tasks [impossible due_date] -> 422
POST /tasks [past due_date is allowed] -> 201

--- list queries ---
[assignee exact, case-insensitive  ] 200 n=2 ['Fix auth bug', 'Review budget']
[assignee partial must NOT match   ] 200 n=0 []
[overdue=true                      ] 200 n=2 ['Fix auth bug', 'Late']
[overdue=false                     ] 200 n=3 ['Review budget', 'Ship homepage redesign', 'Update readme']
[q description-only match          ] 200 n=1 ['Fix auth bug']
[q matches two tasks               ] 200 n=2 ['Review budget', 'Ship homepage redesign']
[q no matches                      ] 200 n=0 []
[q whitespace only                 ] 200 n=5 [...]
[q + status (AND, empty)           ] 200 n=0 []
[all filters                       ] 200 n=1 ['Fix auth bug']
[invalid priority                  ] 422

--- is_overdue per task ---
Fix auth bug               status=todo         due=2026-07-26   overdue=True
Review budget              status=todo         due=2026-07-29   overdue=False
Ship homepage redesign     status=todo         due=2026-08-03   overdue=False
Update readme              status=done         due=None         overdue=False
```

One honest correction: the first contract run reported
`[all filters] 200 n=0 []`, which looked like a bug in the AND logic. It was a
flaw in the *script* — an earlier section patched `priority: low` onto the task
the query expected to be `high`. I fixed the script to restore both fields it
changes, so the "all filters" line is now a meaningful positive case. The
contract was captured after that fix, and both before/after captures use the
fixed script.

---

## 5. Break Tests

A Break Test deliberately introduces a bug, confirms a **named** test catches
it, and then restores. A test that cannot fail is not evidence.

### Break Test 1 — the overdue boundary (Feature 1)

Target: `test_task_due_today_is_not_overdue`.

Change made in `app/business_rules.py`:

```diff
-    return due_date < (reference_date or today())
+    return due_date <= (reference_date or today())  # BREAK TEST - off-by-one
```

Result:

```
=========================== short test summary info ===========================
FAILED tests/test_due_dates.py::test_task_due_today_is_not_overdue - Assertio...
FAILED tests/test_due_dates.py::test_overdue_true_returns_only_overdue_tasks
FAILED tests/test_due_dates.py::test_overdue_false_includes_tasks_with_no_due_date
3 failed, 42 passed in 1.39s
```

With the failure detail:

```
>       assert [task["title"] for task in body] == ["Late"]
E       AssertionError: assert ['Late', 'Due today'] == ['Late']
E         Left contains one more item: 'Due today'
```

**What this proves:** a one-character change to the boundary is caught three
times — once at the unit level and twice through the API. It also shows the
`?overdue=` filter genuinely reuses the single rule; if it had its own copy of
the comparison, the two filter tests would have kept passing.

Restored, re-ran: `45 passed`.

### Break Test 2 — the AND combination and a closure trap (Feature 2)

Target: `test_search_combines_with_assignee` and `test_all_five_filters_at_once`.

This one tests the risk the AI flagged during the refactor: predicates that
close over a reassigned local all see the last value assigned. Change made in
`app/storage.py` — reverting the per-predicate binding to a shared local:

```diff
     if assignee is not None:
-        predicates.append(
-            lambda task, want=assignee.strip().casefold(): (
-                (task.assignee or "").casefold() == want
-            )
-        )
+        needle = assignee.strip().casefold()
+        predicates.append(lambda task: (task.assignee or "").casefold() == needle)
...
     if q is not None and q.strip():
-        predicates.append(
-            lambda task, want=q.strip().casefold(): (
-                want in task.title.casefold()
-                or want in (task.description or "").casefold()
-            )
-        )
+        needle = q.strip().casefold()
+        predicates.append(
+            lambda task: (
+                needle in task.title.casefold()
+                or needle in (task.description or "").casefold()
+            )
+        )
```

Result:

```
=========================== short test summary info ===========================
FAILED tests/test_search_filters.py::test_search_combines_with_assignee - Ass...
FAILED tests/test_search_filters.py::test_all_five_filters_at_once - Assertio...
2 failed, 66 passed in 4.08s
```

The behaviour contract caught it independently:

```
[all filters                       ] 200 n=0 []               =>
[all filters                       ] 200 n=1 ['Fix auth bug'] <=
```

**What this proves, and it is the most useful result in this document:**
**66 of 68 tests passed with a real bug in the code.** Every single-filter test
was green, because the bug only appears when `assignee` and `q` are supplied
together — the assignee predicate ends up comparing the assignee against the
search term. Only the two tests that deliberately *combine* filters failed. If I
had tested each filter in isolation, as the first draft of the suite did, this
would have shipped. It is the reason `test_all_five_filters_at_once` exists.

Restored, re-ran: `68 passed`, and the contract diff returned
`contract IDENTICAL after restore`.

---

## 6. Final state

```bash
pytest
```

```
....................................................................     [100%]
68 passed in 3.94s
```

- `git status` clean; no break-test edits left behind.
- Behaviour contract identical to the pre-refactor capture.
- Browser console clean; both features usable in the UI.
- No secrets committed: `.env` is gitignored, only `.env.example` is tracked,
  and it contains no credentials. `data/` and `venv/` are gitignored.
