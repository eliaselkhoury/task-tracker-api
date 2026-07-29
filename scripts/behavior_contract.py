"""Print the API's observable behaviour for a fixed set of requests.

This is the "behaviour contract" used around refactors: run it, keep the
output, refactor, run it again, and diff. A refactor that changes any line of
this output changed behaviour, which is the definition of not-a-refactor.

It is deliberately independent of the pytest suite - the tests say what should
happen, this says what *does* happen, and diffing catches drift the tests do
not happen to cover.

Usage:
    python scripts/behavior_contract.py > contract.txt
"""

import json
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

# Make the project root importable when run as `python scripts/...`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402

# All dates are expressed relative to today, so the output is stable on any day.
TODAY = date.today()
OFFSETS = {"past": -3, "today": 0, "future": 5}


def iso(offset_days: int) -> str:
    return (TODAY + timedelta(days=offset_days)).isoformat()


# The fixed board every run starts from. Order matters: it is the order the API
# returns tasks in.
SEED = [
    {
        "title": "Fix auth bug",
        "description": "Login fails after the token refresh.",
        "priority": "high",
        "assignee": "Maria",
        "due_date": iso(OFFSETS["past"]),
    },
    {
        "title": "Review budget",
        "description": "Finance needs sign-off.",
        "priority": "medium",
        "assignee": "maria",
        "due_date": iso(OFFSETS["today"]),
    },
    {
        "title": "Ship homepage redesign",
        "description": "Needs sign-off from design.",
        "priority": "high",
        "assignee": "Marc",
        "due_date": iso(OFFSETS["future"]),
    },
    {
        "title": "Update readme",
        "priority": "low",
    },
]

# (label, query string) pairs covering both features and their combination.
QUERIES = [
    ("no filters", ""),
    ("status=todo", "status=todo"),
    ("priority=high", "priority=high"),
    ("assignee exact, case-insensitive", "assignee=MARIA"),
    ("assignee partial must NOT match", "assignee=Mar"),
    ("overdue=true", "overdue=true"),
    ("overdue=false", "overdue=false"),
    ("q title match", "q=auth"),
    ("q description-only match", "q=token"),
    ("q case-insensitive", "q=AUTH"),
    ("q partial word", "q=aut"),
    ("q matches two tasks", "q=sign-off"),
    ("q no matches", "q=kubernetes"),
    ("q whitespace only", "q=%20%20"),
    ("q + priority", "q=sign-off&priority=high"),
    ("q + status (AND, empty)", "q=auth&status=in_progress"),
    ("q + overdue", "q=token&overdue=true"),
    ("all filters", "q=auth&status=todo&priority=high&assignee=Maria&overdue=true"),
    ("invalid priority", "priority=urgent"),
    ("invalid status", "status=archived"),
    ("invalid overdue", "overdue=maybe"),
]


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        # Never touch the developer's real data file.
        settings.data_file = Path(tmp) / "contract.json"
        client = TestClient(app)

        print("=== behaviour contract ===")
        print(f"(dates relative to today: {', '.join(f'{k}={v:+d}d' for k, v in OFFSETS.items())})")
        print()

        print("--- health ---")
        response = client.get("/health")
        print(f"GET /health -> {response.status_code} {json.dumps(response.json())}")
        print()

        print("--- seed ---")
        created = []
        for payload in SEED:
            response = client.post("/tasks", json=payload)
            created.append(response.json())
            print(f"POST /tasks {payload['title']!r} -> {response.status_code}")
        print()

        print("--- validation on create ---")
        for label, payload in [
            ("blank title", {"title": "   "}),
            ("unknown priority", {"title": "x", "priority": "urgent"}),
            ("malformed due_date", {"title": "x", "due_date": "31/12/2026"}),
            ("impossible due_date", {"title": "x", "due_date": "2026-02-30"}),
            ("past due_date is allowed", {"title": "Late", "due_date": iso(-30)}),
        ]:
            response = client.post("/tasks", json=payload)
            print(f"POST /tasks [{label}] -> {response.status_code}")
        print()

        print("--- status transitions ---")
        walker = created[3]["id"]  # "Update readme", starts in todo
        for target in ["done", "in_progress", "done", "todo"]:
            response = client.patch(f"/tasks/{walker}", json={"status": target})
            print(f"PATCH status={target:<12} -> {response.status_code}")
        print()

        print("--- due date updates ---")
        subject = created[0]["id"]  # "Fix auth bug", overdue at seed time
        for label, payload in [
            ("move date", {"due_date": iso(10)}),
            ("unrelated patch keeps date", {"priority": "low"}),
            ("clear date", {"due_date": None}),
            ("malformed date", {"due_date": "soon"}),
        ]:
            response = client.patch(f"/tasks/{subject}", json=payload)
            body = response.json() if response.status_code == 200 else {}
            print(
                f"PATCH [{label:<26}] -> {response.status_code} "
                f"due_date={body.get('due_date')!r} is_overdue={body.get('is_overdue')!r}"
            )
        # Restore both fields this section changed, so the queries below see the
        # board as seeded and the "all filters" case is a real positive match.
        client.patch(
            f"/tasks/{subject}",
            json={"due_date": iso(OFFSETS["past"]), "priority": "high"},
        )
        print()

        print("--- not found ---")
        for method in ["get", "patch", "delete"]:
            call = getattr(client, method)
            response = (
                call("/tasks/missing", json={"title": "x"})
                if method == "patch"
                else call("/tasks/missing")
            )
            print(f"{method.upper():<6} /tasks/missing -> {response.status_code}")
        print()

        print("--- list queries ---")
        for label, query in QUERIES:
            path = f"/tasks?{query}" if query else "/tasks"
            response = client.get(path)
            if response.status_code != 200:
                print(f"[{label:<34}] {response.status_code}")
                continue
            titles = [task["title"] for task in response.json()]
            print(f"[{label:<34}] 200 n={len(titles)} {titles}")
        print()

        print("--- is_overdue per task ---")
        for task in client.get("/tasks").json():
            print(
                f"{task['title']:<26} status={task['status']:<12} "
                f"due={str(task['due_date']):<12} overdue={task['is_overdue']}"
            )


if __name__ == "__main__":
    main()
