# Reflection

**Tools.** Claude Code (Opus 5) in the terminal did most of the work: planning
the two features, drafting the backend and tests, and running pytest and the
behaviour contract in a loop. GitHub Copilot's inline suggestions handled the
repetitive parts — the filter-bar markup, the pill CSS variants, the parametrised
list of malformed dates. Copilot is good at continuing a pattern I have already
established, and a poor place to decide anything. Every decision in the ADR came
from a conversation where I asked for the trade-off before the code.

**Where AI clearly helped.** The overdue rule. I asked it to argue both sides of
computing "overdue" in the backend versus the frontend, and it started out
leaning frontend — fewer bytes, no server work. Then it worked through the
timezone case and reversed itself: if the badge uses the browser's clock and the
`?overdue=true` filter uses the server's, a card can be returned by the filter
and rendered with no badge. I had not thought about it, and I would have written
the JS version because it looked cheaper. That argument became decision 2 in the
ADR and the reason `is_overdue` is a server-derived field. It also caught its own
follow-on bug: `new Date("2026-08-04")` parses as UTC midnight and renders as
Aug 3 west of Greenwich.

**Where it slowed me down.** Scope. Asked for a debounced search box, it returned
a debounce helper plus an `AbortController`, a loading spinner, and a query
cache. All plausible, all real code I then had to read and reject. The earlier
"add due dates" prompt was worse: it invented a sort control, changed
`GET /tasks` to return an envelope, and added a validator refusing past due
dates — which would have made the app unable to represent the exact situation the
feature exists to highlight. The time went on reviewing work I did not want.
Naming the files it could touch, and the response shape it could not change,
fixed this more than any other habit.

**Where my review changed the result.** I told it twice to keep `assignee` an
exact match. The diff made it a substring match anyway, to mirror the new `q`
logic. I caught it reading the diff, not from a failing test — the baseline had
no test for the assignee filter, so the suite would have gone green and
`assignee=Mar` would quietly have matched both Maria and Marc. I kept the exact
match and added two tests to pin it.

The Break Tests turned that instinct into evidence. Reverting one binding in the
refactored filter code left **66 of 68 tests passing** with a real bug present:
every single-filter test was green, because the bug only surfaced when two
filters combined. That is the lesson I am keeping. AI is fast at producing code
that passes the tests you thought to write, so the review has to ask what the
tests do not cover — and then a test has to be added for it.
