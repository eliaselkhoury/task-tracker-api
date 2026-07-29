"""Pydantic models: the request/response contract for the Task Tracker API.

Three shapes per resource:
  * TaskCreate   - what a client may send when creating a task.
  * TaskUpdate   - what a client may send when patching a task (all optional).
  * TaskResponse - what the API always sends back.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


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


def utc_now() -> datetime:
    """Current time as a timezone-aware UTC timestamp.

    Centralised so every stored timestamp is comparable and tests can patch
    a single function instead of chasing datetime.now() calls.
    """
    return datetime.now(timezone.utc)
