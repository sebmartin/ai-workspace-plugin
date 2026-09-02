"""Session files and the stub created on a session's first write.

The stub exists so that a todo or decision written mid-session can link to the
session it came out of before that session has been saved. It also means a
session that dies without being saved still leaves a record of what it touched,
where previously nothing at all was written.
"""

from datetime import date
from pathlib import Path

from ai_workspace.threads.v2 import ids as ids_mod
from ai_workspace.threads.v2 import index as idx

STUB_MARKER = "status: unsaved"


def session_path(thread_dir: Path, session_id: str) -> Path:
    return thread_dir / "sessions" / f"{session_id}.md"


def ensure_stub(thread_dir: Path, slug: str, today: date | None = None) -> str:
    """Create the session file and its index entry if absent. Returns the id."""
    today = today or date.today()
    base_id = ids_mod.make_id(today, slug)
    # Idempotent: called repeatedly through one session, this is the same
    # session, so an existing file for the same day and slug is reused rather
    # than uniquified into a second stub.
    if session_path(thread_dir, base_id).exists():
        return base_id
    session_id = ids_mod.unique_id(base_id, idx.taken_ids(thread_dir, "sessions"))
    path = session_path(thread_dir, session_id)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\n"
            f"date: {today.isoformat()}\n"
            f"{STUB_MARKER}\n"
            "---\n\n"
            f"# Session: {slug} - {today.isoformat()}\n\n"
            "## Created during this session\n\n"
        )
        idx.add(
            thread_dir, "sessions",
            idx.Entry(session_id, None, slug, f"./sessions/{session_id}.md"),
        )
    return session_id


def note_created(thread_dir: Path, session_id: str, line: str) -> None:
    """Record something the session produced, so an unsaved session still says so."""
    path = session_path(thread_dir, session_id)
    if not path.exists():
        return
    text = path.read_text()
    if STUB_MARKER not in text:
        return
    marker = "## Created during this session\n\n"
    if marker in text:
        head, _, tail = text.partition(marker)
        text = head + marker + tail.rstrip("\n") + ("\n" if tail.strip() else "") + f"- {line}\n"
    else:
        text = text.rstrip() + f"\n\n{marker}- {line}\n"
    path.write_text(text)
