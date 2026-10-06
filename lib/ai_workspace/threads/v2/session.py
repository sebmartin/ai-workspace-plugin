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


def ensure_stub(thread_dir: Path, slug: str, today: date | None = None) -> str:
    """Create the session file and its index entry if absent. Returns the id.

    The index title is the slug as the id spells it, not as it was passed. The
    two are the same for the kebab-case the tool asks for, and a session's
    title then agrees with its id the way a decision's and an artifact's do.
    Passed through raw, a slug carrying `]` wrote a line the index could not
    read back.
    """
    today = today or date.today()
    base_id = ids_mod.make_id(today, slug)
    title = ids_mod.slugify(slug)
    # Idempotent: called repeatedly through one session, this is the same
    # session, so an existing file for the same day and slug is reused rather
    # than uniquified into a second stub. The index entry is checked either
    # way, since a file can exist without one when it was written directly.
    taken = idx.taken_ids(thread_dir, "sessions")
    if session_path(thread_dir, base_id).exists():
        session_id = base_id
    else:
        session_id = ids_mod.unique_id(base_id, taken)
        path = session_path(thread_dir, session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\n"
            f"date: {today.isoformat()}\n"
            "---\n\n"
            f"# Session: {title} - {today.isoformat()}\n"
        )
    if session_id not in taken:
        idx.add(
            thread_dir, "sessions",
            idx.Entry(session_id, None, title, f"./sessions/{session_id}.md"),
        )
    return session_id


def save(thread_dir: Path, slug: str, summary: str, keywords: str, body: str,
         today: date | None = None) -> tuple[str, str]:
    """Write the session log. Returns (session_id, note).

    The body replaces whatever the file holds.
    """
    today = today or date.today()
    session_id = ensure_stub(thread_dir, slug, today=today)
    path = session_path(thread_dir, session_id)
    front = (
        "---\n"
        f"date: {today.isoformat()}\n"
        f"summary: {yaml_value(summary)}\n"
        f"keywords: {yaml_value(keywords)}\n"
        "---\n\n"
    )
    path.write_text(front + body.rstrip() + "\n")

    entries = idx.read(thread_dir, "sessions")
    entry = idx.find(entries, session_id)
    title = ids_mod.slugify(slug)
    if entry is not None and slug and entry.title != title:
        entry.title = title
        idx.write(thread_dir, "sessions", entries)
    return session_id, "saved"
