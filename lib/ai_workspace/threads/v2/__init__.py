"""Schema 2: the indexes are the record, the README is a view."""

# unchanged from v1
from ai_workspace.threads.v1 import links

# changed in v2
# new in v2: nothing older has indexes to write to
from ai_workspace.threads.v2.ops import (
    add_todo,
    index_directory,
    index_file,
    log_decision,
    order_todos,
    retire_artifact,
    retire_decision,
    retire_todo,
    save_session,
    set_about,
    set_state,
    star_artifact,
    unstar_artifact,
)
from ai_workspace.threads.v2.thread import about, create, resume

__all__ = [
    "about",
    "add_todo",
    "create",
    "index_directory",
    "index_file",
    "links",
    "log_decision",
    "order_todos",
    "resume",
    "retire_artifact",
    "retire_decision",
    "retire_todo",
    "save_session",
    "set_about",
    "set_state",
    "star_artifact",
    "unstar_artifact",
]
