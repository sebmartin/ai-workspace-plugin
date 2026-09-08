"""Write operations on a schema 2 thread.

Each one appends or moves a single line and then re-renders, so the README's
derived section always equals the projection of its index. The assistant
supplies fields; this module owns the line format and id uniqueness, which is
what keeps `^- <id>:` lookups reliable.

None of these carries a large payload, so none of them can be defeated by the
model's per-response output cap.
"""

from datetime import date
from pathlib import Path, PurePosixPath

from ai_workspace.text import split_frontmatter, yaml_value
from ai_workspace.threads.v2 import dates, render, session
from ai_workspace.threads.v2 import ids as ids_mod
from ai_workspace.threads.v2 import index as idx


def _new_id(thread_dir: Path, kind: str, title: str) -> str:
    """An id for something being created now. Only todos: everything else is a
    file, and a file's id comes off its name through `index_file`."""
    return ids_mod.unique_id(
        ids_mod.make_id(date.today(), title), idx.taken_ids(thread_dir, kind)
    )


# What each kind gets when a file is indexed. Sessions carry no state at all,
# artifacts have exactly one in-force state so it needs no deciding, and
# decisions have three so theirs is read from the file.
_STATE_FROM_FILE = object()
_INDEXABLE = {
    "sessions": (None, False),
    "decisions": (_STATE_FROM_FILE, False),
    "artifacts": ("current", True),
}


def _decision_state(path: Path) -> str | None:
    """A decision's status, if the file states a valid one."""
    try:
        fields, _ = split_frontmatter(path.read_text(errors="ignore")[:2000], path)
    except (OSError, ValueError):
        return None
    status = str(fields.get("status") or "").strip()
    return status if status in idx.IN_FORCE["decisions"] else None


def index_file(thread, link: str, description: str = "",
               session_id: str | None = None) -> str:
    """Index a file that is already in the thread.

    The only function that mints an index entry for a file; the tools that
    author one call it once they have written it. Everything on the line is
    derived from the file, which is what keeps an id and its basename in
    agreement and leaves nothing to invent.

    It refuses a link that does not resolve, so it cannot be used to register
    something that does not exist yet. That is the whole boundary between this
    and the authoring tools.
    """
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    # Not lstrip("./"), which strips every leading dot and slash and would turn
    # `../../elsewhere` into `elsewhere` before anything got to object to it.
    relative = PurePosixPath(link[2:] if link.startswith("./") else link)
    if relative.is_absolute() or ".." in relative.parts or len(relative.parts) < 2:
        return f"Error: '{link}' is not a path to a file inside the thread."

    kind = relative.parts[0]
    if kind not in _INDEXABLE:
        allowed = ", ".join(_INDEXABLE)
        return f"Error: '{kind}' is not an indexable directory. Use one of: {allowed}."

    path = thread.dir / relative
    if not path.exists():
        return f"Error: Nothing at {link}. Write the file before indexing it."

    default_state, takes_description = _INDEXABLE[kind]
    if default_state is _STATE_FROM_FILE:
        state = _decision_state(path)
        if state is None:
            allowed = ", ".join(idx.IN_FORCE["decisions"])
            return (
                f"Error: {link} does not declare a status this schema knows.\n"
                f"Set `status:` in its frontmatter to one of: {allowed}."
            )
    else:
        state = default_state

    when, rest = ids_mod.from_filename(path.name)
    if when is None:
        when = dates.from_a_session_naming(thread.dir, path.name)
    entry_id = ids_mod.unique_id(
        ids_mod.make_id(when, rest), idx.taken_ids(thread.dir, kind)
    )

    idx.add(thread.dir, kind, idx.Entry(
        entry_id, state, entry_id, f"./{relative}",
        description if takes_description else "",
    ))
    render.render(thread.dir)
    _record(thread.dir, session_id, f"{kind[:-1]} {entry_id}")
    dated = "" if when else " Its date could not be derived, so it is marked unknown."
    return f"Indexed {entry_id}.{dated}"


def _record(thread_dir: Path, session_id: str | None, line: str) -> None:
    if session_id:
        session.note_created(thread_dir, session_id, line)


def add_todo(thread, title: str, link: str, state: str = "active",
             session_id: str | None = None) -> str:
    if state not in idx.IN_FORCE["todos"]:
        allowed = ", ".join(idx.IN_FORCE["todos"])
        return f"Error: '{state}' is not a todo state. Use one of: {allowed}."
    if not link:
        return ("Error: a todo needs a link. Use the session it came out of when it "
                "has no file or issue of its own — a bare line cannot be expanded later.")
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    todo_id = _new_id(thread.dir, "todos", title)
    idx.add(thread.dir, "todos", idx.Entry(todo_id, state, title, link))
    render.render(thread.dir)
    _record(thread.dir, session_id, f"todo {todo_id}")
    return f"Added todo {todo_id} ({state})."


def retire_todo(thread, todo_id: str, state: str) -> str:
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    error = idx.retire(thread.dir, "todos", todo_id, state)
    if error:
        return error
    _drop_from_windows(thread.dir, "todos", todo_id)
    render.render(thread.dir)
    return f"Retired todo {todo_id} as {state}."


def set_state(thread, kind: str, entry_id: str, state: str) -> str:
    """Move an entry between in-force states, e.g. parking or unparking a todo."""
    if state not in idx.IN_FORCE[kind]:
        allowed = ", ".join(idx.IN_FORCE[kind])
        return f"Error: '{state}' is not an in-force {kind} state. Use one of: {allowed}."
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    entries, fm = idx.read(thread.dir, kind)
    entry = idx.find(entries, entry_id)
    if entry is None:
        return f"Error: No {kind} entry with id '{entry_id}'."
    entry.state = state
    idx.write(thread.dir, kind, entries, fm)
    render.render(thread.dir)
    return f"{entry_id} is now {state}."


def set_window(thread, kind: str, section: str, entry_ids: list[str]) -> str:
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    error = idx.set_window(thread.dir, kind, section, entry_ids)
    if error:
        return error
    render.render(thread.dir)
    return f"Window '{section}' set to {len(entry_ids)} item(s)."


def _drop_from_windows(thread_dir: Path, kind: str, entry_id: str) -> None:
    entries, fm = idx.read(thread_dir, kind)
    windows = fm.get("windows") or {}
    changed = False
    for name, members in windows.items():
        if entry_id in members:
            windows[name] = [m for m in members if m != entry_id]
            changed = True
    if changed:
        idx.write(thread_dir, kind, entries, {"windows": windows})


def log_decision(thread, title: str, summary: str, body: str,
                 status: str = "proposed", supersedes: list[str] | None = None,
                 session_id: str | None = None) -> str:
    if status not in idx.IN_FORCE["decisions"]:
        allowed = ", ".join(idx.IN_FORCE["decisions"])
        return f"Error: '{status}' is not an in-force decision status. Use one of: {allowed}."
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    supersedes = supersedes or []
    decision_id = ids_mod.unique_id(
        ids_mod.make_id(date.today(), title), idx.taken_ids(thread.dir, "decisions")
    )
    path = thread.dir / "decisions" / f"{decision_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    front = [
        "---",
        f"title: {yaml_value(title)}",
        f"status: {status}",
        f"summary: {yaml_value(summary)}",
        f"supersedes: [{', '.join(supersedes)}]",
        "---",
        "",
    ]
    path.write_text("\n".join(front) + body.rstrip() + "\n")
    # Indexed the same way a pre-existing file is, so the id it just chose for
    # the filename is the id that lands on the line. Nothing can disagree.
    indexed = index_file(thread, f"./decisions/{decision_id}.md", session_id=session_id)
    if indexed.startswith("Error:"):
        return indexed

    # `supersedes` on the live decision is the only direction that gets followed:
    # traversal starts from what is in force, so a dead-to-live pointer is one
    # nobody reads. Retiring the replaced ones here is what makes that true.
    retired = []
    for old in supersedes:
        if idx.retire(thread.dir, "decisions", old, "superseded") is None:
            retired.append(old)
    if retired:
        render.render(thread.dir)
    note = f" Superseded {', '.join(retired)}." if retired else ""
    return f"Logged decision {decision_id} ({status}) at ./decisions/{decision_id}.md.{note}"


def retire_decision(thread, decision_id: str, state: str) -> str:
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    entries, _ = idx.read(thread.dir, "decisions")
    entry = idx.find(entries, decision_id)
    error = idx.retire(thread.dir, "decisions", decision_id, state)
    if error:
        return error
    # Keep the file's own status in step, so a decision found by grep or in a
    # file browser says what it is without depending on which index led there.
    if entry:
        path = thread.dir / entry.link.lstrip("./")
        if path.is_file():
            text = path.read_text()
            for live in idx.IN_FORCE["decisions"]:
                if f"status: {live}" in text:
                    path.write_text(text.replace(f"status: {live}", f"status: {state}", 1))
                    break
    render.render(thread.dir)
    return f"Retired decision {decision_id} as {state}."


def retire_artifact(thread, artifact_id: str, state: str) -> str:
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    error = idx.retire(thread.dir, "artifacts", artifact_id, state)
    if error:
        return error
    render.render(thread.dir)
    return f"Retired artifact {artifact_id} as {state}."
