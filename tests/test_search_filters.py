"""Feature 2 - text search and combined filters on GET /tasks."""

from datetime import date, datetime, timedelta, timezone

import pytest


def iso(value: date) -> str:
    return value.isoformat()


def server_today() -> date:
    """The UTC date, which is what the server compares due dates against.

    Not `server_today()` - see the same helper in test_due_dates.py for why.
    """
    return datetime.now(timezone.utc).date()


@pytest.fixture
def board(make_task):
    """A small board with deliberate overlaps so AND-combination is testable.

    Titles and descriptions are chosen so that some searches match a title,
    some match only a description, and some match more than one task.
    """
    return {
        "auth": make_task(
            title="Fix auth bug",
            description="Login fails after the token refresh.",
            priority="high",
            assignee="Maria",
        ),
        "redesign": make_task(
            title="Ship homepage redesign",
            description="Needs sign-off from design.",
            priority="high",
            status="in_progress",
            assignee="Marc",
        ),
        "budget": make_task(
            title="Review budget",
            description="Finance needs sign-off.",
            priority="medium",
            assignee="maria",
        ),
        "readme": make_task(
            title="Update readme",
            priority="low",
        ),
    }


def titles(response):
    return sorted(task["title"] for task in response.json())


# --- searching -----------------------------------------------------------


def test_search_matches_the_title(board, client):
    response = client.get("/tasks", params={"q": "auth"})

    assert response.status_code == 200
    assert titles(response) == ["Fix auth bug"]


def test_search_matches_the_description(board, client):
    """'token' appears only in a description, never in a title."""
    response = client.get("/tasks", params={"q": "token"})

    assert titles(response) == ["Fix auth bug"]


def test_search_is_case_insensitive(board, client):
    assert titles(client.get("/tasks", params={"q": "AUTH"})) == ["Fix auth bug"]
    assert titles(client.get("/tasks", params={"q": "aUtH"})) == ["Fix auth bug"]


def test_search_matches_partial_words(board, client):
    assert titles(client.get("/tasks", params={"q": "aut"})) == ["Fix auth bug"]


def test_search_can_match_several_tasks(board, client):
    """'sign-off' appears in two different descriptions."""
    assert titles(client.get("/tasks", params={"q": "sign-off"})) == [
        "Review budget",
        "Ship homepage redesign",
    ]


def test_search_with_no_matches_returns_200_and_empty_list(board, client):
    response = client.get("/tasks", params={"q": "kubernetes"})

    assert response.status_code == 200
    assert response.json() == []


def test_whitespace_only_search_is_treated_as_no_search(board, client):
    """A user who taps space in the search box should not empty the board."""
    response = client.get("/tasks", params={"q": "   "})

    assert len(response.json()) == 4


def test_empty_search_string_returns_everything(board, client):
    assert len(client.get("/tasks", params={"q": ""}).json()) == 4


def test_search_ignores_tasks_with_no_description(board, client):
    """A null description must not blow up the substring check."""
    response = client.get("/tasks", params={"q": "readme"})

    assert titles(response) == ["Update readme"]


def test_search_does_not_match_the_id_or_timestamps(board, client):
    """Search is scoped to title and description on purpose."""
    task_id = board["auth"]["id"]

    assert client.get("/tasks", params={"q": task_id}).json() == []


# --- the assignee filter stays exact ------------------------------------


def test_list_tasks_filters_by_assignee(board, client):
    """Baseline behaviour, pinned here so Feature 2 cannot widen it.

    The AI's draft made `assignee` a substring match like `q`. That would make
    `assignee=Mar` match both Maria and Marc. See docs/midcourse/mini-adr.md,
    decision 5.
    """
    assert titles(client.get("/tasks", params={"assignee": "Marc"})) == [
        "Ship homepage redesign"
    ]


def test_assignee_filter_is_case_insensitive_but_still_exact(board, client):
    """'maria' and 'Maria' are the same person; 'Mar' is not a person."""
    assert titles(client.get("/tasks", params={"assignee": "MARIA"})) == [
        "Fix auth bug",
        "Review budget",
    ]
    assert client.get("/tasks", params={"assignee": "Mar"}).json() == []


# --- combining filters --------------------------------------------------


def test_search_combines_with_priority(board, client):
    response = client.get("/tasks", params={"q": "sign-off", "priority": "high"})

    assert titles(response) == ["Ship homepage redesign"]


def test_search_combines_with_status_and_priority(board, client):
    response = client.get(
        "/tasks",
        params={"q": "redesign", "priority": "high", "status": "in_progress"},
    )

    assert titles(response) == ["Ship homepage redesign"]


def test_combined_filters_are_and_not_or(board, client):
    """'auth' matches a task, but that task is not in_progress, so: no results."""
    response = client.get("/tasks", params={"q": "auth", "status": "in_progress"})

    assert response.status_code == 200
    assert response.json() == []


def test_search_combines_with_assignee(board, client):
    response = client.get("/tasks", params={"q": "sign-off", "assignee": "maria"})

    assert titles(response) == ["Review budget"]


def test_search_combines_with_overdue(board, client, make_task):
    """Feature 1's filter and Feature 2's search have to work together."""
    make_task(
        title="Overdue sign-off chase",
        description="Chase the sign-off.",
        due_date=iso(server_today() - timedelta(days=2)),
    )

    response = client.get("/tasks", params={"q": "sign-off", "overdue": "true"})

    assert titles(response) == ["Overdue sign-off chase"]


def test_all_five_filters_at_once(board, client, make_task):
    make_task(
        title="Late high-priority audit",
        description="Security audit overdue.",
        priority="high",
        status="in_progress",
        assignee="Maria",
        due_date=iso(server_today() - timedelta(days=1)),
    )

    response = client.get(
        "/tasks",
        params={
            "q": "audit",
            "status": "in_progress",
            "priority": "high",
            "assignee": "Maria",
            "overdue": "true",
        },
    )

    assert titles(response) == ["Late high-priority audit"]


def test_no_filters_returns_everything(board, client):
    assert len(client.get("/tasks").json()) == 4


# --- invalid filter values ----------------------------------------------


def test_unknown_priority_value_returns_422(board, client):
    response = client.get("/tasks", params={"priority": "urgent"})

    assert response.status_code == 422


def test_unknown_status_value_returns_422(board, client):
    response = client.get("/tasks", params={"status": "archived"})

    assert response.status_code == 422


def test_overlong_search_string_returns_422(board, client):
    response = client.get("/tasks", params={"q": "x" * 201})

    assert response.status_code == 422


# --- filtering does not change the stored data -------------------------


def test_filtering_does_not_mutate_the_store(board, client):
    """A GET with filters must be read-only."""
    client.get("/tasks", params={"q": "auth", "status": "todo", "overdue": "false"})

    assert len(client.get("/tasks").json()) == 4
