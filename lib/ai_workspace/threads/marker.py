"""The file that declares which schema a thread uses.

A leaf on purpose. Both the registry and every schema that writes a marker need
this, and keeping it here means neither has to import the other: a schema that
imported the registry would close a loop, since the registry imports every
schema.

Absence means schema 1. That schema predates versioning and never wrote the
file, so it cannot be detected any other way.
"""

from pathlib import Path

NAME = "schema-version"


def read(thread_dir: Path) -> int | None:
    """The thread's schema, or None if the marker is present but unreadable.

    The value is always read, never inferred from the file merely existing.
    That inference holds only while exactly one schema writes the file and
    breaks silently as soon as a second does, in the worst direction, where an
    older plugin sees a marker it does not understand and hands the thread to
    the wrong reader.
    """
    marker = thread_dir / NAME
    if not marker.exists():
        return 1
    try:
        return int(marker.read_text().strip())
    except (OSError, ValueError):
        return None


def write(thread_dir: Path, schema: int) -> None:
    (thread_dir / NAME).write_text(f"{schema}\n")
