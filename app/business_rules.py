"""Domain rules that are not simple field validation.

Keeping these out of the route handlers means they can be unit-tested
without spinning up an HTTP client.
"""

from datetime import date
from typing import Optional

from app.models import TaskStatus, today


class BusinessRuleError(ValueError):
    """Raised when a request is well-formed but violates a domain rule."""


# A task moves through the board one step at a time. Jumping straight from
# "todo" to "done" skips the work, so it is rejected; moving backwards is
# allowed because people do reopen tasks.
ALLOWED_STATUS_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.todo: {TaskStatus.todo, TaskStatus.in_progress},
    TaskStatus.in_progress: {TaskStatus.in_progress, TaskStatus.todo, TaskStatus.done},
    TaskStatus.done: {TaskStatus.done, TaskStatus.in_progress},
}


def validate_status_transition(current: TaskStatus, new: TaskStatus) -> None:
    """Allow or reject a status change.

    Raises:
        BusinessRuleError: if `new` is not reachable from `current`.
    """
    if new not in ALLOWED_STATUS_TRANSITIONS[current]:
        allowed = ", ".join(sorted(s.value for s in ALLOWED_STATUS_TRANSITIONS[current]))
        raise BusinessRuleError(
            f"cannot move a task from '{current.value}' to '{new.value}'; "
            f"allowed next values are: {allowed}"
        )


def is_task_overdue(
    due_date: Optional[date],
    status: TaskStatus,
    reference_date: Optional[date] = None,
) -> bool:
    """Return True when a task's deadline has passed and it is not finished.

    Three rules, each of which has a test:
      * no due date  -> never overdue
      * due today    -> not overdue (the day is not over yet)
      * status done  -> not overdue, even if the date has passed

    Args:
        due_date: the task's deadline, or None.
        status: the task's current status.
        reference_date: what counts as "today". Defaults to the server's date;
            passed explicitly by tests so they do not depend on the real clock.
    """
    if due_date is None:
        return False
    if status is TaskStatus.done:
        return False
    return due_date < (reference_date or today())
