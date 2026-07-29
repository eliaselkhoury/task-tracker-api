"""Status-transition rules, tested both as a unit and through the API."""

import pytest

from app.business_rules import BusinessRuleError, validate_status_transition
from app.models import TaskStatus


def test_todo_to_in_progress_is_allowed():
    validate_status_transition(TaskStatus.todo, TaskStatus.in_progress)


def test_todo_to_done_is_rejected():
    with pytest.raises(BusinessRuleError):
        validate_status_transition(TaskStatus.todo, TaskStatus.done)


def test_done_can_be_reopened_to_in_progress():
    validate_status_transition(TaskStatus.done, TaskStatus.in_progress)


def test_patch_status_todo_to_done_returns_409(make_task, client):
    created = make_task(title="Skip the work")

    response = client.patch(f"/tasks/{created['id']}", json={"status": "done"})

    assert response.status_code == 409
    assert "cannot move a task" in response.json()["detail"]


def test_patch_status_walks_the_board(make_task, client):
    created = make_task(title="Do it properly")
    task_id = created["id"]

    assert client.patch(f"/tasks/{task_id}", json={"status": "in_progress"}).status_code == 200
    assert client.patch(f"/tasks/{task_id}", json={"status": "done"}).status_code == 200
    assert client.get(f"/tasks/{task_id}").json()["status"] == "done"
