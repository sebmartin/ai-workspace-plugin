"""Dating a file whose own name does not say when it is from.

Only reached when `ids.from_filename` finds nothing. Sessions register what they
create, so a session naming the file dates it.

It searches for that one basename rather than extracting every filename-shaped
token from every session and building a map. The token form matched `e.g.` and
`github.com` as readily as a real filename, and it read the whole thread to
answer a question about one file.

Migration indexes sessions before anything else, so every session read here has
already been migrated. That is what keeps schema 2 code from ever reading a
schema 1 file.
"""

from datetime import date
from pathlib import Path

from ai_workspace.threads.v2 import ids
from ai_workspace.threads.v2 import index as idx


def from_a_session_naming(thread_dir: Path, basename: str) -> date | None:
    """The earliest session whose text contains this filename, if any.

    Oldest first, so the first hit is the session that created the file rather
    than a later one referring back to it.
    """
    sessions = thread_dir / "sessions"
    if not sessions.is_dir():
        return None

    dated = []
    for path in sessions.iterdir():
        if not idx.is_content(path):
            continue
        when, _ = ids.from_filename(path.name)
        if when is not None:
            dated.append((when, path))

    for when, path in sorted(dated, key=lambda pair: (pair[0], pair[1].name)):
        try:
            if basename in path.read_text(errors="ignore"):
                return when
        except OSError:
            continue
    return None
