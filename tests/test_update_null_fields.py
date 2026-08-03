"""Explicit nulls in PATCH /tasks/{id} must never reach the JSON store.

Regression tests for a data-corruption bug found in review. Sending
`{"title": null}` returned 500 *after* writing the null to data/tasks.json, so
every later GET also returned 500 and a server restart did not help - the app
reloaded the same corrupted file. `{"priority": null}` did the same.

Two things are asserted throughout:
  * the request is rejected with 422, not a 500
  * the store is byte-for-byte untouched, so nothing is corrupted

`description`, `assignee` and `due_date` are genuinely nullable - null is how a
client clears them - so those must keep returning 200.
"""

import json

import pytest

# Fields that always have a value on a task. Null is not a way to unset them,
# so an explicit null is invalid input.
NON_NULLABLE_FIELDS = ["title", "status", "priority"]

# Fields where null is the documented way to clear the value.
NULLABLE_FIELDS = ["description", "assignee", "due_date"]


@pytest.fixture
def existing_task(make_task):
    return make_task(
        title="Important task",
        description="Do not lose this.",
        priority="high",
        assignee="Maria",
        due_date="2026-09-01",
    )


# --- explicit null on a non-nullable field is rejected -------------------


@pytest.mark.parametrize("field", NON_NULLABLE_FIELDS)
def test_patch_null_on_non_nullable_field_returns_422(existing_task, client, field):
    response = client.patch(f"/tasks/{existing_task['id']}", json={field: None})

    assert response.status_code == 422


@pytest.mark.parametrize("field", NON_NULLABLE_FIELDS)
def test_patch_null_leaves_the_stored_task_unchanged(existing_task, client, field):
    """The rejected update must not have been applied."""
    client.patch(f"/tasks/{existing_task['id']}", json={field: None})

    task = client.get(f"/tasks/{existing_task['id']}").json()
    assert task[field] == existing_task[field]
    assert task["updated_at"] == existing_task["updated_at"]


@pytest.mark.parametrize("field", NON_NULLABLE_FIELDS)
def test_patch_null_writes_nothing_to_disk(existing_task, client, field, isolated_store):
    """The strongest form of the guarantee: the file does not change at all."""
    before = isolated_store.read_bytes()

    client.patch(f"/tasks/{existing_task['id']}", json={field: None})

    assert isolated_store.read_bytes() == before


@pytest.mark.parametrize("field", NON_NULLABLE_FIELDS)
def test_api_still_works_after_a_rejected_null_update(existing_task, client, field):
    """The bug's real damage: every later read failed, permanently.

    A 500 on one bad request is bad. A 500 on every request afterwards, which
    survives a restart because the corruption is on disk, is much worse.
    """
    client.patch(f"/tasks/{existing_task['id']}", json={field: None})

    listing = client.get("/tasks")
    assert listing.status_code == 200
    assert [task["title"] for task in listing.json()] == ["Important task"]


@pytest.mark.parametrize("field", NON_NULLABLE_FIELDS)
def test_stored_json_never_holds_a_null_for_these_fields(
    existing_task, client, field, isolated_store
):
    client.patch(f"/tasks/{existing_task['id']}", json={field: None})

    stored = json.loads(isolated_store.read_text(encoding="utf-8"))
    assert stored[0][field] is not None


# --- nullable fields must keep working ----------------------------------


@pytest.mark.parametrize("field", NULLABLE_FIELDS)
def test_patch_null_on_nullable_field_clears_it(existing_task, client, field):
    """Regression guard in the other direction: do not over-tighten the fix."""
    response = client.patch(f"/tasks/{existing_task['id']}", json={field: None})

    assert response.status_code == 200
    assert response.json()[field] is None


def test_clearing_several_nullable_fields_at_once(existing_task, client):
    response = client.patch(
        f"/tasks/{existing_task['id']}",
        json={"description": None, "assignee": None, "due_date": None},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["description"] is None
    assert body["assignee"] is None
    assert body["due_date"] is None
    # The non-nullable fields are untouched.
    assert body["title"] == "Important task"
    assert body["priority"] == "high"


# --- neighbouring bad input, same guarantee -----------------------------


def test_blank_title_is_rejected_without_touching_disk(
    existing_task, client, isolated_store
):
    before = isolated_store.read_bytes()

    response = client.patch(f"/tasks/{existing_task['id']}", json={"title": "   "})

    assert response.status_code == 422
    assert isolated_store.read_bytes() == before


def test_wrong_type_is_rejected_without_touching_disk(
    existing_task, client, isolated_store
):
    before = isolated_store.read_bytes()

    response = client.patch(f"/tasks/{existing_task['id']}", json={"title": 12345})

    assert response.status_code == 422
    assert isolated_store.read_bytes() == before


def test_illegal_status_transition_does_not_touch_disk(
    existing_task, client, isolated_store
):
    """409 is a rejection too, so it must also leave the file alone."""
    before = isolated_store.read_bytes()

    response = client.patch(f"/tasks/{existing_task['id']}", json={"status": "done"})

    assert response.status_code == 409
    assert isolated_store.read_bytes() == before


def test_a_valid_update_still_writes(existing_task, client, isolated_store):
    """Make sure the guard does not block legitimate writes."""
    response = client.patch(f"/tasks/{existing_task['id']}", json={"title": "Renamed"})

    assert response.status_code == 200
    stored = json.loads(isolated_store.read_text(encoding="utf-8"))
    assert stored[0]["title"] == "Renamed"
