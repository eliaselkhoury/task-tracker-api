"""Pydantic models: the request/response contract for the Task Tracker API.

Three shapes per resource:
  * TaskCreate   - what a client may send when creating a task.
  * TaskUpdate   - what a client may send when patching a task (all optional).
  * TaskResponse - what the API always sends back.
"""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class TaskStatus(str, Enum):
    """The three Kanban columns."""

    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class TaskPriority(str, Enum):
    """How urgent a task is. Rendered as a coloured pill on the card."""

    low = "low"
    medium = "medium"
    high = "high"


def _clean_optional_text(value: Optional[str]) -> Optional[str]:
    """Trim surrounding whitespace and treat an empty string as 'not set'."""
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


class TaskBase(BaseModel):
    """Fields shared by create and response models."""

    title: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: TaskStatus = TaskStatus.todo
    priority: TaskPriority = TaskPriority.medium
    assignee: Optional[str] = Field(default=None, max_length=80)

    # A calendar day, not a timestamp: users mean "by the end of this day", and
    # a date avoids picking an hour and a timezone for them. Deliberately not
    # validated against today - a task that was already due last week is a
    # legitimate thing to enter, and should show up as overdue rather than be
    # refused. See docs/midcourse/mini-adr.md, decisions 1 and 3.
    due_date: Optional[date] = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        """A title of only spaces is a blank title, not a valid one."""
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("title must not be blank")
        return trimmed

    @field_validator("description", "assignee")
    @classmethod
    def normalise_optional_text(cls, value: Optional[str]) -> Optional[str]:
        return _clean_optional_text(value)


class TaskCreate(TaskBase):
    """Payload for POST /tasks."""


class TaskUpdate(BaseModel):
    """Payload for PATCH /tasks/{task_id}.

    Every field is optional: only the keys actually present in the request
    body are applied, so a partial update never clears untouched fields.
    """

    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee: Optional[str] = Field(default=None, max_length=80)

    # Sending `"due_date": null` explicitly clears the date; omitting the key
    # entirely leaves it untouched. `exclude_unset` in storage.update_task is
    # what makes those two cases distinguishable.
    due_date: Optional[date] = None

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_nulls(cls, data: Any) -> Any:
        """Refuse `null` for fields a task always has.

        Every field here is Optional, but that only means "may be omitted" - it
        does not mean the underlying task field is nullable. Only description,
        assignee and due_date can actually be cleared; a task always has a
        title, a status and a priority.

        Without this check, `{"title": null}` was accepted as a change, written
        to the JSON store, and only then failed when the response model rejected
        it - leaving a task on disk with a null title that made every subsequent
        read fail. Rejecting it here turns that 500 into a 422.
        """
        if isinstance(data, dict):
            for field in ("title", "status", "priority"):
                if field in data and data[field] is None:
                    raise ValueError(
                        f"{field} cannot be null; omit the field to leave it unchanged"
                    )
        return data

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("title must not be blank")
        return trimmed

    @field_validator("description", "assignee")
    @classmethod
    def normalise_optional_text(cls, value: Optional[str]) -> Optional[str]:
        return _clean_optional_text(value)


class TaskResponse(TaskBase):
    """Everything the API returns for a task, including server-owned fields."""

    id: str
    created_at: datetime
    updated_at: datetime

    # Derived on read from due_date, status and the server's current date - it
    # is never stored, because a stored value goes stale at midnight. The
    # backend owns this so the card badge and the ?overdue= filter can never
    # disagree. See docs/midcourse/mini-adr.md, decision 2.
    is_overdue: bool = False


def utc_now() -> datetime:
    """Current time as a timezone-aware UTC timestamp.

    Centralised so every stored timestamp is comparable and tests can patch
    a single function instead of chasing datetime.now() calls.
    """
    return datetime.now(timezone.utc)


def today() -> date:
    """The server's current date, used as the reference point for 'overdue'.

    Separate from utc_now() so a test can freeze the day without freezing the
    created_at/updated_at timestamps it is not interested in.
    """
    return utc_now().date()
