"""Feature 1 - due dates and the overdue filter.

The overdue rule is deliberately tested against a fixed reference date where
possible, so these tests do not start failing on a particular calendar day.
Where a test goes through the HTTP API it uses dates relative to `server_today()`
- see the note on that function for why it is not `server_today()`.
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.business_rules import is_task_overdue
from app.models import TaskStatus

TODAY = date(2026, 7, 29)
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)


def iso(value: date) -> str:
    return value.isoformat()


def server_today() -> date:
    """The date the server will compare due dates against: the UTC date.

    Not `server_today()`. The app derives "overdue" from `app.models.today()`,
    which is `utc_now().date()`, while `server_today()` is the *local* date. In a
    positive UTC offset - Beirut is UTC+3 - those two disagree between 00:00
    and 03:00 local, when UTC is still on the previous day.

    Building an API test's due dates from the local date made three tests fail
    in that window and pass the rest of the day. CI never caught it because
    GitHub runners are UTC, so local and UTC agree there. Deriving them from
    the same clock the server uses removes the window entirely, without the
    test having to import the app's own `today()` and lose the ability to catch
    a bug in it.
    """
    return datetime.now(timezone.utc).date()


# --- the rule itself, as a unit ------------------------------------------


def test_task_with_no_due_date_is_never_overdue():
    assert is_task_overdue(None, TaskStatus.todo, reference_date=TODAY) is False


def test_task_due_yesterday_is_overdue():
    assert is_task_overdue(YESTERDAY, TaskStatus.todo, reference_date=TODAY) is True


def test_task_due_today_is_not_overdue():
    """The day is not over yet, so 'due today' is on time."""
    assert is_task_overdue(TODAY, TaskStatus.in_progress, reference_date=TODAY) is False


def test_task_due_tomorrow_is_not_overdue():
    assert is_task_overdue(TOMORROW, TaskStatus.todo, reference_date=TODAY) is False


def test_done_task_is_not_overdue_even_when_late():
    """Finished work cannot be late - it is finished."""
    assert is_task_overdue(YESTERDAY, TaskStatus.done, reference_date=TODAY) is False


# --- create / read through the API ---------------------------------------


def test_create_task_with_due_date(client):
    response = client.post(
        "/tasks", json={"title": "Ship it", "due_date": iso(TOMORROW)}
    )

    assert response.status_code == 201
    assert response.json()["due_date"] == iso(TOMORROW)


def test_create_task_without_due_date_leaves_it_null(client):
    response = client.post("/tasks", json={"title": "Someday"})

    assert response.status_code == 201
    body = response.json()
    assert body["due_date"] is None
    assert body["is_overdue"] is False


@pytest.mark.parametrize(
    "bad_value",
    ["31/12/2026", "not-a-date", "2026-13-45", "2026-02-30", ""],
)
def test_create_task_rejects_malformed_due_date(client, bad_value):
    response = client.post("/tasks", json={"title": "Bad date", "due_date": bad_value})

    assert response.status_code == 422


def test_create_task_accepts_a_past_due_date(client):
    """A task that was already due is legitimate input, not a validation error.

    This pins down the AI assumption I rejected: its first draft returned 422
    for any date before today. See docs/midcourse/user-stories.md.
    """
    past = server_today() - timedelta(days=10)

    response = client.post("/tasks", json={"title": "Late already", "due_date": iso(past)})

    assert response.status_code == 201
    body = response.json()
    assert body["due_date"] == iso(past)
    assert body["is_overdue"] is True


def test_is_overdue_is_present_on_every_task(make_task, client):
    make_task(title="No date")
    make_task(title="With date", due_date=iso(server_today() + timedelta(days=3)))

    body = client.get("/tasks").json()

    assert all("is_overdue" in task for task in body)


# --- update -------------------------------------------------------------


def test_patch_can_change_the_due_date(make_task, client):
    created = make_task(title="Move it", due_date=iso(server_today()))
    new_date = iso(server_today() + timedelta(days=7))

    response = client.patch(f"/tasks/{created['id']}", json={"due_date": new_date})

    assert response.status_code == 200
    assert response.json()["due_date"] == new_date


def test_patch_with_explicit_null_clears_the_due_date(make_task, client):
    past = server_today() - timedelta(days=2)
    created = make_task(title="Was late", due_date=iso(past))
    assert created["is_overdue"] is True

    response = client.patch(f"/tasks/{created['id']}", json={"due_date": None})

    assert response.status_code == 200
    body = response.json()
    assert body["due_date"] is None
    assert body["is_overdue"] is False


def test_patch_without_due_date_key_preserves_it(make_task, client):
    """An unrelated update must not wipe the deadline."""
    due = iso(server_today() + timedelta(days=5))
    created = make_task(title="Keep my date", due_date=due)

    response = client.patch(f"/tasks/{created['id']}", json={"priority": "high"})

    assert response.status_code == 200
    body = response.json()
    assert body["priority"] == "high"
    assert body["due_date"] == due


def test_patch_rejects_malformed_due_date(make_task, client):
    created = make_task(title="Valid for now")

    response = client.patch(f"/tasks/{created['id']}", json={"due_date": "soon"})

    assert response.status_code == 422


def test_completing_a_late_task_clears_its_overdue_flag(make_task, client):
    past = iso(server_today() - timedelta(days=3))
    created = make_task(title="Finish late work", due_date=past)
    task_id = created["id"]

    client.patch(f"/tasks/{task_id}", json={"status": "in_progress"})
    body = client.patch(f"/tasks/{task_id}", json={"status": "done"}).json()

    assert body["status"] == "done"
    assert body["due_date"] == past
    assert body["is_overdue"] is False


# --- the ?overdue= filter -----------------------------------------------


@pytest.fixture
def board_with_mixed_due_dates(make_task, client):
    """Four tasks: one late, one due today, one future, one with no date."""
    late = make_task(title="Late", due_date=iso(server_today() - timedelta(days=1)))
    due_today = make_task(title="Due today", due_date=iso(server_today()))
    future = make_task(title="Future", due_date=iso(server_today() + timedelta(days=4)))
    no_date = make_task(title="No date")
    return {"late": late, "due_today": due_today, "future": future, "no_date": no_date}


def test_overdue_true_returns_only_overdue_tasks(board_with_mixed_due_dates, client):
    body = client.get("/tasks", params={"overdue": "true"}).json()

    assert [task["title"] for task in body] == ["Late"]


def test_overdue_false_includes_tasks_with_no_due_date(
    board_with_mixed_due_dates, client
):
    body = client.get("/tasks", params={"overdue": "false"}).json()

    assert sorted(task["title"] for task in body) == ["Due today", "Future", "No date"]


def test_omitting_overdue_returns_everything(board_with_mixed_due_dates, client):
    body = client.get("/tasks").json()

    assert len(body) == 4


def test_overdue_filter_excludes_done_tasks(make_task, client):
    """A late task that gets finished drops out of ?overdue=true."""
    created = make_task(title="Late then done", due_date=iso(server_today() - timedelta(days=5)))
    task_id = created["id"]

    assert len(client.get("/tasks", params={"overdue": "true"}).json()) == 1

    client.patch(f"/tasks/{task_id}", json={"status": "in_progress"})
    client.patch(f"/tasks/{task_id}", json={"status": "done"})

    assert client.get("/tasks", params={"overdue": "true"}).json() == []


def test_overdue_filter_with_no_matches_returns_200_and_empty_list(make_task, client):
    make_task(title="Future", due_date=iso(server_today() + timedelta(days=30)))

    response = client.get("/tasks", params={"overdue": "true"})

    assert response.status_code == 200
    assert response.json() == []


def test_overdue_rejects_a_non_boolean_value(client):
    response = client.get("/tasks", params={"overdue": "maybe"})

    assert response.status_code == 422
