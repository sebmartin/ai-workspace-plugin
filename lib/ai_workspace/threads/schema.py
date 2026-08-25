"""Which on-disk schema a thread uses, and which module implements it.

The schema is declared by a `schema-version` file at the thread root holding a
single integer. Absence means schema 1: that schema predates versioning and
never wrote the file, so it cannot be detected any other way.

The value is always read, never inferred from the file merely existing. That
inference holds only while exactly one schema writes the file and breaks
silently as soon as a second does, in the worst direction, where an older
plugin sees a marker it does not understand and hands the thread to the wrong
reader.

Separate from __init__.py so the registry, the Thread record and the counters
stay one readable unit and __init__.py stays the API.
"""

from pathlib import Path
from typing import NamedTuple

from ai_workspace.threads import v1

MARKER = "schema-version"

SCHEMAS = {1: v1}

MIN_READABLE_SCHEMA = 1
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


def read_schema(thread_dir: Path) -> int | None:
    """Return the thread's schema, or None if the marker is unreadable.

    Absent marker means schema 1. A marker that is present but not an integer
    is None, which callers surface as an error rather than guessing.
    """
    marker = thread_dir / MARKER
    if not marker.exists():
        return 1
    try:
        return int(marker.read_text().strip())
    except (OSError, ValueError):
        return None


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
    supported = (
        f"{MIN_READABLE_SCHEMA}"
        if MIN_READABLE_SCHEMA == CURRENT_SCHEMA
        else f"{MIN_READABLE_SCHEMA} to {CURRENT_SCHEMA}"
    )
    if schema is None:
        return (
            f"Error: UNREADABLE_SCHEMA\n"
            f"Thread '{thread_name}' has a {MARKER} file that is not an integer.\n"
            f"This plugin reads schema {supported}."
        )
    return (
        f"Error: UNSUPPORTED_SCHEMA\n"
        f"Thread '{thread_name}' is schema {schema}; this plugin reads {supported}."
    )
