"""Schema 2: the indexes are the record, the README is a view."""

# changed in v2
from ai_workspace.threads.v2.thread import create, resume
# new in v2: nothing older has indexes to write to
from ai_workspace.threads.v2.ops import (
    add_artifact,
    add_todo,
    log_decision,
    retire_artifact,
    retire_decision,
    retire_todo,
    set_state,
    set_window,
)

__all__ = [
    "add_artifact",
    "add_todo",
    "create",
    "log_decision",
    "resume",
    "retire_artifact",
    "retire_decision",
    "retire_todo",
    "set_state",
    "set_window",
]
