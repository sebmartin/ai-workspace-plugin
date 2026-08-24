"""Write operations on a schema 2 thread.

Each one appends or moves a single line and then re-renders, so the README's
derived section always equals the projection of its index. The assistant
supplies fields; this module owns the line format and id uniqueness, which is
what keeps `^- <id>:` lookups reliable.

None of these carries a large payload, so none of them can be defeated by the
model's per-response output cap.
"""

from datetime import date
from pathlib import Path

from ai_workspace.threads.v2 import ids as ids_mod
from ai_workspace.threads.v2 import index as idx
from ai_workspace.threads.v2 import render, session


def _today() -> str:
    return date.today().isoformat()


def _new_id(thread_dir: Path, kind: str, title: str, when: str | None = None) -> str:
    return ids_mod.unique_id(
        ids_mod.make_id(when or _today(), title), idx.taken_ids(thread_dir, kind)
    )


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
    todo_id = _new_id(thread.dir, "todos", title)
    idx.append(thread.dir, "todos", idx.Entry(todo_id, state, title, link))
    render.render(thread.dir)
    _record(thread.dir, session_id, f"todo {todo_id}")
    return f"Added todo {todo_id} ({state})."


def retire_todo(thread, todo_id: str, state: str) -> str:
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
    entries, fm = idx.read(thread.dir, kind)
    entry = idx.find(entries, entry_id)
    if entry is None:
        return f"Error: No {kind} entry with id '{entry_id}'."
    entry.state = state
    idx.write(thread.dir, kind, entries, fm)
    render.render(thread.dir)
    return f"{entry_id} is now {state}."


def set_window(thread, kind: str, section: str, entry_ids: list[str]) -> str:
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
    supersedes = supersedes or []
    decision_id = _new_id(thread.dir, "decisions", title)
    path = thread.dir / "decisions" / f"{decision_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    front = [
        "---",
        f"title: {title}",
        f"status: {status}",
        f"summary: {summary}",
        f"supersedes: [{', '.join(supersedes)}]",
        "---",
        "",
    ]
    path.write_text("\n".join(front) + body.rstrip() + "\n")
    idx.append(thread.dir, "decisions",
               idx.Entry(decision_id, status, title, f"./decisions/{decision_id}.md"))

    # `supersedes` on the live decision is the only direction that gets followed:
    # traversal starts from what is in force, so a dead-to-live pointer is one
    # nobody reads. Retiring the replaced ones here is what makes that true.
    retired = []
    for old in supersedes:
        if idx.retire(thread.dir, "decisions", old, "superseded") is None:
            retired.append(old)
    render.render(thread.dir)
    _record(thread.dir, session_id, f"decision {decision_id}")
    note = f" Superseded {', '.join(retired)}." if retired else ""
    return f"Logged decision {decision_id} ({status}) at ./decisions/{decision_id}.md.{note}"


def retire_decision(thread, decision_id: str, state: str) -> str:
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


def add_artifact(thread, title: str, link: str,
                 session_id: str | None = None) -> str:
    artifact_id = _new_id(thread.dir, "artifacts", title)
    idx.append(thread.dir, "artifacts", idx.Entry(artifact_id, "current", title, link))
    render.render(thread.dir)
    _record(thread.dir, session_id, f"artifact {artifact_id}")
    return f"Added artifact {artifact_id}."


def retire_artifact(thread, artifact_id: str, state: str) -> str:
    error = idx.retire(thread.dir, "artifacts", artifact_id, state)
    if error:
        return error
    render.render(thread.dir)
    return f"Retired artifact {artifact_id} as {state}."
