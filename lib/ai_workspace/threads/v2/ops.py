"""Write operations on a schema 2 thread.

Each one appends or moves a single line and then re-renders, so the README's
derived section always equals the projection of its index. The assistant
supplies fields; this module owns the line format and id uniqueness, which is
what keeps `^- <id>:` lookups reliable.

None of these carries a large payload, so none of them can be defeated by the
model's per-response output cap.
"""

import json
from datetime import date
from pathlib import Path, PurePosixPath
from typing import NamedTuple

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


class Refusal(NamedTuple):
    """Why one file could not be indexed: a code, and what differs per file.

    A code rather than a sentence. No human reads a tool result, so the
    sentence explaining what `FRONTMATTER_UNPARSEABLE` means is filler here and
    belongs in the tool's docstring, which is read once instead of once per
    failure. `detail` is only what the code cannot carry, and only ever varies
    per file: a parser's position, or the status a file actually declared.
    """

    code: str
    detail: str = ""


def _decision_state(path: Path) -> tuple[str | None, Refusal | None]:
    """A decision's status, or why it has none.

    Two different faults, and reporting the wrong one sends the reader to the
    wrong fix. A file whose frontmatter is invalid YAML usually states a
    perfectly good status; it just cannot be read.
    """
    try:
        fields, _ = split_frontmatter(path.read_text(errors="ignore")[:2000], path)
    except OSError as e:
        return None, Refusal("UNREADABLE", str(e))
    except ValueError as e:
        # The parser's own complaint, which names a line and a column and the
        # real fault. Guessing at a cause here would send the reader to the
        # wrong fix whenever the guess was wrong.
        return None, Refusal("FRONTMATTER_UNPARSEABLE", str(e))
    status = str(fields.get("status") or "").strip()
    if status in idx.IN_FORCE["decisions"]:
        return status, None
    return None, Refusal("STATUS_UNKNOWN", status)


def _inside(link: str) -> PurePosixPath | None:
    """A thread-relative path, or None if it points outside the thread.

    Not lstrip("./"), which strips every leading dot and slash and would turn
    `../../elsewhere` into `elsewhere` before anything got to object to it.
    """
    relative = PurePosixPath(link[2:] if link.startswith("./") else link)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        return None
    return relative


def _index_one(thread, link: str, description: str = "") -> tuple[str, Refusal | None]:
    """Derive an entry for one existing file and add it. `(entry_id, error)`.

    No render: the caller does that once, so indexing sixty-six sessions
    rewrites the README once rather than sixty-six times.
    """
    relative = _inside(link)
    if relative is None or len(relative.parts) < 2:
        return "", Refusal("OUTSIDE_THREAD")

    kind = relative.parts[0]
    if kind not in _INDEXABLE:
        return "", Refusal("NOT_INDEXABLE", kind)

    path = thread.dir / relative
    if not path.exists():
        return "", Refusal("MISSING")
    if not idx.is_content(path):
        return "", Refusal("METADATA")

    default_state, takes_description = _INDEXABLE[kind]
    if default_state is _STATE_FROM_FILE:
        state, refusal = _decision_state(path)
        if refusal is not None:
            return "", refusal
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
    return entry_id, None


def index_file(thread, link: str, description: str = "",
               session_id: str | None = None) -> str:
    """Index a file that is already in the thread.

    The only way an index entry for a file is minted; the tools that author one
    call it once they have written it. Everything on the line is derived from
    the file, which is what keeps an id and its basename in agreement and
    leaves nothing to invent.

    It refuses a link that does not resolve, so it cannot register something
    that does not exist yet. That is the whole boundary between this and the
    authoring tools.
    """
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    entry_id, refusal = _index_one(thread, link, description)
    if refusal is not None:
        return json.dumps({"error": refusal.code, "detail": refusal.detail})
    render.render(thread.dir)
    _record(thread.dir, session_id, f"{PurePosixPath(link).parts[-2][:-1]} {entry_id}")
    reply: dict = {"id": entry_id}
    if entry_id.startswith(ids_mod.UNKNOWN):
        reply["undated"] = True
    return json.dumps(reply)


def index_directory(thread, link: str, session_id: str | None = None) -> str:
    """Index every top-level entry in one directory that is not indexed yet.

    Migration is the reason this exists. A thread with sixty-six sessions is
    sixty-six identical calls otherwise, and for sessions and decisions there is
    nothing per-file to say: everything on the line is read off the file. Only
    artifacts carry a description, so those are still worth indexing one at a
    time when the description matters.

    Idempotent, so a run that refused some decisions can be repeated after
    fixing them without duplicating the ones that went in. A refusal is reported
    and does not stop the rest.
    """
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    relative = _inside(link)
    if relative is None or len(relative.parts) != 1:
        return json.dumps({"error": "OUTSIDE_THREAD", "detail": link})

    kind = relative.parts[0]
    if kind not in _INDEXABLE:
        return json.dumps({"error": "NOT_INDEXABLE", "detail": kind})

    directory = thread.dir / relative
    if not directory.is_dir():
        # Not silence. `create` lays down all three indexable directories, so a
        # missing one means the thread is malformed or the caller named a kind
        # it did not mean, and both want saying.
        return json.dumps({"error": "NO_SUCH_DIRECTORY", "detail": kind})

    already = {
        PurePosixPath(e.link).name
        for retired in (False, True)
        for e in idx.read(thread.dir, kind, retired)[0]
    }
    pending = sorted(
        p for p in directory.iterdir()
        if idx.is_content(p) and p.name not in already
    )

    indexed, unknown = [], []
    refused: dict[str, list[str]] = {}
    for path in pending:
        entry_id, refusal = _index_one(thread, f"./{kind}/{path.name}")
        if refusal is not None:
            refused.setdefault(refusal.code, []).append(path.name)
            continue
        indexed.append(entry_id)
        if entry_id.startswith(ids_mod.UNKNOWN):
            unknown.append(entry_id)

    if indexed:
        render.render(thread.dir)
        _record(thread.dir, session_id, f"{len(indexed)} {kind} indexed")

    # No news is good news. Asking to index a directory and being told every
    # file went in is a hundred filenames of nothing; the caller asked for all
    # of them and silence says it got them. Only deviations come back: what was
    # refused, and what had to be dated at the epoch.
    reply: dict = {}
    if unknown:
        reply["undated"] = [i[len(ids_mod.UNKNOWN) + 1:] for i in unknown]
    if refused:
        reply["refused"] = refused
    return json.dumps(reply)


def _record(thread_dir: Path, session_id: str | None, line: str) -> None:
    if session_id:
        session.note_created(thread_dir, session_id, line)


def add_todo(thread, title: str, link: str, state: str = "active",
             session_id: str | None = None) -> str:
    if state not in idx.IN_FORCE["todos"]:
        allowed = list(idx.IN_FORCE["todos"])
        return json.dumps({"error": "STATE_UNKNOWN", "detail": state, "allowed": allowed})
    if not link:
        return json.dumps({"error": "LINK_REQUIRED"})
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    todo_id = _new_id(thread.dir, "todos", title)
    idx.add(thread.dir, "todos", idx.Entry(todo_id, state, title, link))
    render.render(thread.dir)
    _record(thread.dir, session_id, f"todo {todo_id}")
    return json.dumps({"id": todo_id})


def retire_todo(thread, todo_id: str, state: str) -> str:
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    error = idx.retire(thread.dir, "todos", todo_id, state)
    if error:
        return error
    _drop_from_windows(thread.dir, "todos", todo_id)
    render.render(thread.dir)
    return json.dumps({"id": todo_id})


def set_state(thread, kind: str, entry_id: str, state: str) -> str:
    """Move an entry between in-force states, e.g. parking or unparking a todo."""
    if state not in idx.IN_FORCE[kind]:
        return json.dumps({"error": "STATE_UNKNOWN", "detail": state,
                           "allowed": list(idx.IN_FORCE[kind])})
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    entries, fm = idx.read(thread.dir, kind)
    entry = idx.find(entries, entry_id)
    if entry is None:
        return json.dumps({"error": "NO_SUCH_ENTRY", "detail": entry_id})
    entry.state = state
    idx.write(thread.dir, kind, entries, fm)
    render.render(thread.dir)
    return json.dumps({"id": entry_id})


def set_window(thread, kind: str, section: str, entry_ids: list[str]) -> str:
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    error = idx.set_window(thread.dir, kind, section, entry_ids)
    if error:
        return error
    render.render(thread.dir)
    return json.dumps({"window": section, "size": len(entry_ids)})


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
        return json.dumps({"error": "STATUS_UNKNOWN", "detail": status,
                           "allowed": list(idx.IN_FORCE["decisions"])})
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
    reply: dict = {"id": decision_id}
    if retired:
        reply["superseded"] = retired
    return json.dumps(reply)


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
    return json.dumps({"id": decision_id})


def retire_artifact(thread, artifact_id: str, state: str) -> str:
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    error = idx.retire(thread.dir, "artifacts", artifact_id, state)
    if error:
        return error
    render.render(thread.dir)
    return json.dumps({"id": artifact_id})


def save_session(thread, slug: str, summary: str, keywords: str,
                 next_context: str, body: str | None = None,
                 status: str | None = None) -> str:
    """Everything a save does that is not synthesis.

    The incremental tools have already written todos, decisions and artifacts as
    they happened, so a save is down to the session log and the Status
    paragraph. A session that dies before this still leaves its stub and a
    record of what it touched.
    """
    from ai_workspace.threads.v2 import readme as readme_mod

    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    session_id, _ = session.save(thread.dir, slug, summary, keywords, next_context, body)
    if status:
        readme_mod.set_status(thread.dir, status)
    readme_mod.touch_dates(thread.dir)
    render.render(thread.dir)
    return json.dumps({"id": session_id, "status_written": bool(status)})
