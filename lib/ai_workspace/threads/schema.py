"""Which on-disk schema a thread uses, and which module implements it.

The schema is declared by a marker file at the thread root; reading and writing
it is marker.py's job, kept separate so a schema can write one without
importing this module and closing a loop.

Separate from __init__.py so the registry, the Thread record and the counters
stay one readable unit and __init__.py stays the API.
"""

from pathlib import Path
from typing import NamedTuple

from ai_workspace.threads import v1, v2
from ai_workspace.threads.marker import NAME as MARKER  # noqa: F401  (re-exported)
from ai_workspace.threads.marker import read as read_schema  # noqa: F401  (re-exported)

SCHEMAS = {1: v1, 2: v2}

MIN_READABLE_SCHEMA = min(SCHEMAS)

# What the plugin creates, which lags what it can read: schema 2 threads cannot
# be saved until the write tools land, so create still produces schema 1.
CURRENT_SCHEMA = 1


class Thread(NamedTuple):
    """A resolved thread. Plain data: where it is, and which schema reads it."""

    workspace: Path
    name: str
    dir: Path
    schema: int


def implementation(thread: Thread):
    """The module implementing this thread's schema."""
    return SCHEMAS[thread.schema]


def at(workspace: Path, name: str, directory: Path) -> tuple[Thread | None, str | None]:
    """Build a record for a thread directory. Exactly one of the pair is None.

    Takes the directory rather than deriving it, because restore has to resolve
    a schema while the thread is still staged outside threads/.
    """
    schema = read_schema(directory)
    if schema is None or schema not in SCHEMAS:
        return None, unsupported_message(name, schema)
    return Thread(workspace, name, directory, schema), None


def unsupported_message(thread_name: str, schema: int | None) -> str:
    """Explain a refusal in schema terms only.

    Never names a plugin release: that would need a schema-to-release mapping
    in code, which is the coupling the separate counters exist to avoid.
    """
    low, high = min(SCHEMAS), max(SCHEMAS)
    supported = f"{low}" if low == high else f"{low} to {high}"
    if schema is None:
        return (
            f"Error: UNREADABLE_SCHEMA\n"
            f"Thread '{thread_name}' has a {MARKER} file that is not an integer.\n"
            f"This plugin reads schema {supported}."
        )
    if schema > high:
        return (
            f"Error: SCHEMA_TOO_NEW\n"
            f"Thread '{thread_name}' is schema {schema}; this plugin reads {supported}.\n"
            f"Upgrade the plugin to work with this thread."
        )
    return (
        f"Error: SCHEMA_RETIRED\n"
        f"Thread '{thread_name}' is schema {schema}; this plugin reads {supported}.\n"
        f"Migrate it with a plugin version that still reads schema {schema}."
    )
