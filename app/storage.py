"""JSON-file storage layer.

The whole task list lives in one JSON file. Every read loads the file and
every write rewrites it. That is deliberately simple: the point of the
course project is the API and the workflow, not database tuning.

Only this module knows about the file format. Routes talk to it through
functions that take and return Pydantic models.
"""

import json
import uuid
from pathlib import Path
from typing import Any, Optional

from app.business_rules import is_task_overdue, validate_status_transition
from app.core.config import settings
from app.models import (
    TaskCreate,
    TaskPriority,
    TaskResponse,
    TaskStatus,
    TaskUpdate,
    utc_now,
)


class TaskNotFoundError(LookupError):
    """Raised when a task id does not exist in the store."""


def _data_file() -> Path:
    """Resolve the data file at call time so tests can redirect it."""
    return Path(settings.data_file)


def _read_all() -> list[dict[str, Any]]:
    """Return every stored task as a raw dict, or [] if the file is absent."""
    path = _data_file()
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        content = handle.read().strip()
    if not content:
        return []
    return json.loads(content)


def _write_all(records: list[dict[str, Any]]) -> None:
    """Persist the full task list, creating the parent directory if needed."""
    path = _data_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2, default=str)


def _to_response(record: dict[str, Any]) -> TaskResponse:
    """Validate a stored dict back into the response model.

    `is_overdue` is filled in here rather than read from the file: it depends on
    today's date, so a stored copy would be wrong the next day.
    """
    task = TaskResponse.model_validate(record)
    return task.model_copy(
        update={"is_overdue": is_task_overdue(task.due_date, task.status)}
    )


def add_task(payload: TaskCreate) -> TaskResponse:
    """Create a task, assign it an id and timestamps, and store it."""
    now = utc_now()
    record = payload.model_dump(mode="json")
    record["id"] = str(uuid.uuid4())
    record["created_at"] = now.isoformat()
    record["updated_at"] = now.isoformat()

    records = _read_all()
    records.append(record)
    _write_all(records)
    return _to_response(record)


def list_tasks(
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    assignee: Optional[str] = None,
    overdue: Optional[bool] = None,
    q: Optional[str] = None,
) -> list[TaskResponse]:
    """Return stored tasks, optionally narrowed by the given filters.

    Filters combine with AND. A filter left as None is ignored.

    `overdue` is tri-state: None means "do not filter", True means overdue only,
    False means everything that is not overdue - which includes tasks that have
    no due date at all.

    `q` is a case-insensitive substring search over title and description. It is
    the only fuzzy filter: `assignee` stays an exact match, because "show me
    Maria's tasks" and "find the card about auth" are different questions. See
    docs/midcourse/mini-adr.md, decision 5.
    """
    tasks = [_to_response(record) for record in _read_all()]

    if status is not None:
        tasks = [t for t in tasks if t.status == status]
    if priority is not None:
        tasks = [t for t in tasks if t.priority == priority]
    if assignee is not None:
        needle = assignee.strip().casefold()
        tasks = [t for t in tasks if (t.assignee or "").casefold() == needle]
    if overdue is not None:
        tasks = [t for t in tasks if t.is_overdue == overdue]
    if q is not None and q.strip():
        needle = q.strip().casefold()
        tasks = [
            t
            for t in tasks
            if needle in t.title.casefold()
            or needle in (t.description or "").casefold()
        ]

    return tasks


def get_task(task_id: str) -> TaskResponse:
    """Return one task by id.

    Raises:
        TaskNotFoundError: if no task has that id.
    """
    for record in _read_all():
        if record.get("id") == task_id:
            return _to_response(record)
    raise TaskNotFoundError(task_id)


def update_task(task_id: str, payload: TaskUpdate) -> TaskResponse:
    """Apply a partial update to a task and return the updated version.

    Only keys present in the request body are applied, so omitted fields keep
    their current values. A status change is checked against the transition
    rules before anything is written.

    Raises:
        TaskNotFoundError: if no task has that id.
        BusinessRuleError: if the requested status change is not allowed.
    """
    records = _read_all()

    for index, record in enumerate(records):
        if record.get("id") != task_id:
            continue

        changes = payload.model_dump(mode="json", exclude_unset=True)

        if "status" in changes:
            validate_status_transition(
                TaskStatus(record["status"]), TaskStatus(changes["status"])
            )

        record.update(changes)
        record["updated_at"] = utc_now().isoformat()
        records[index] = record
        _write_all(records)
        return _to_response(record)

    raise TaskNotFoundError(task_id)


def delete_task(task_id: str) -> None:
    """Remove a task by id.

    Raises:
        TaskNotFoundError: if no task has that id.
    """
    records = _read_all()
    remaining = [r for r in records if r.get("id") != task_id]
    if len(remaining) == len(records):
        raise TaskNotFoundError(task_id)
    _write_all(remaining)


def reset() -> None:
    """Empty the store. Used by tests and by local manual resets."""
    _write_all([])
