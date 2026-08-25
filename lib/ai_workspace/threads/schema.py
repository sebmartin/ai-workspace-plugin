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
from ai_workspace.threads.marker import NAME as MARKER
from ai_workspace.threads.marker import read as read_schema

SCHEMAS = {1: v1, 2: v2}

MIN_READABLE_SCHEMA = min(SCHEMAS)

# What the plugin creates. It lagged what the plugin could read while schema 2
# had no way to save; now that it does, new threads get it.
CURRENT_SCHEMA = 2


class Thread(NamedTuple):
    """A resolved thread. Plain data: where it is, and which schema reads it."""

    workspace: Path
    name: str
    dir: Path
    schema: int


def implementation(thread: Thread):
    """The module implementing this thread's schema."""
    return SCHEMAS[thread.schema]


def at(workspace: Path, name: str, directory: Path) -> Thread | str:
    """Build a record for a thread directory, or say why there isn't one."""
    schema = read_schema(directory)
    if schema is None or schema not in SCHEMAS:
        return unsupported_message(name, schema)
    return Thread(workspace, name, directory, schema)


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


def needs_migration_message(thread_name: str, schema: int) -> str:
    """A refusal for an operation this thread's schema does not have.

    Names the schema rather than the operation's absence, because "your thread
    is older than this feature" is the actionable form.
    """
    return (
        f"Status: NEEDS_MIGRATION\n"
        f"Thread '{thread_name}' is schema {schema}, which does not support this "
        f"operation.\n"
        f"Offer to migrate the thread, then retry."
    )
