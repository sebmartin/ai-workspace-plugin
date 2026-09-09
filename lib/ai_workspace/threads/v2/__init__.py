"""Schema 2: the indexes are the record, the README is a view."""

# changed in v2
# new in v2: nothing older has indexes to write to
from ai_workspace.threads.v2.ops import (
    add_todo,
    index_directory,
    index_file,
    log_decision,
    retire_artifact,
    retire_decision,
    retire_todo,
    set_state,
    set_window,
)
from ai_workspace.threads.v2.thread import create, resume

__all__ = [
    "add_todo",
    "create",
    "index_directory",
    "index_file",
    "log_decision",
    "resume",
    "retire_artifact",
    "retire_decision",
    "retire_todo",
    "set_state",
    "set_window",
]
