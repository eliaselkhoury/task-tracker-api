"""Domain rules that are not simple field validation.

Keeping these out of the route handlers means they can be unit-tested
without spinning up an HTTP client.
"""

from app.models import TaskStatus


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
