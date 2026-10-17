"""Session files, and the id and index entry a session gets when it is saved.

What a session produced is recoverable without reading it: every todo,
decision and artifact carries its own dated id and sits in an index.
"""

from datetime import date
from pathlib import Path

from ai_workspace.text import yaml_value
from ai_workspace.threads.v2 import ids as ids_mod
from ai_workspace.threads.v2 import index as idx


def session_path(thread_dir: Path, session_id: str) -> Path:
    return thread_dir / "sessions" / f"{session_id}.md"


def next_id(thread_dir: Path, slug: str, today: date) -> str:
    """The id this session's file takes. Names it; writes nothing.

    The same id on a second save for the same day and slug, because that is the
    same session, so an existing file is reused rather than uniquified into a
    second one beside it.
    """
    base_id = ids_mod.make_id(today, slug)
    if session_path(thread_dir, base_id).exists():
        return base_id
    return ids_mod.unique_id(base_id, idx.taken_ids(thread_dir, "sessions"))


def ensure_indexed(thread_dir: Path, session_id: str, title: str) -> None:
    """Give this session an index line, or correct the title on the one it has.

    The title is the slug as the id spells it, not as it was passed, so a
    session's title agrees with its id the way a decision's and an artifact's
    do. Passed through raw, a slug carrying `]` wrote a line the index could
    not read back. Beyond the id's length cap the two agree on the shortened
    spelling rather than the full slug, which is the same bargain.
    """
    entries = idx.read(thread_dir, "sessions")
    entry = idx.find(entries, session_id)
    if entry is None:
        idx.add(
            thread_dir, "sessions",
            idx.Entry(session_id, None, title, f"./sessions/{session_id}.md"),
        )
    elif entry.title != title:
        entry.title = title
        idx.write(thread_dir, "sessions", entries)


def save(thread_dir: Path, slug: str, summary: str, keywords: str, body: str,
         today: date | None = None) -> tuple[str, str]:
    """Write the session log. Returns (session_id, note).

    The body replaces whatever the file holds. Written before the index points
    at it, so there is no moment where an entry names a file that is not there,
    which is what the migration audit reports as dangling.
    """
    today = today or date.today()
    session_id = next_id(thread_dir, slug, today)
    path = session_path(thread_dir, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    front = (
        "---\n"
        f"date: {today.isoformat()}\n"
        f"summary: {yaml_value(summary)}\n"
        f"keywords: {yaml_value(keywords)}\n"
        "---\n\n"
    )
    path.write_text(front + body.rstrip() + "\n")
    ensure_indexed(thread_dir, session_id, ids_mod.slugify(slug))
    return session_id, "saved"
