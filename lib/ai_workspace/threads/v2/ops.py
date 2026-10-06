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
from ai_workspace.threads.v2 import ids as ids_mod
from ai_workspace.threads.v2 import index as idx
from ai_workspace.threads.v2 import render, session
from ai_workspace.threads.v2 import todos as todos_mod


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

# An artifact description is read on every resume, so it is charged forever
# where the file it describes is opened almost never. A migration carrying them
# out of a v1 README averaged 255 characters and they became 30% of that
# thread's payload. This refuses rather than truncating: a slug cut short is
# still an identifier, where a sentence cut short reads as whole and the reader
# cannot tell. Refusing also reaches the only party that can fix it, since the
# caller wrote the sentence and is still holding it. The same field is checked
# against the line format, which is what a line break in it defeats.
MAX_DESCRIPTION = 200


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


def _already_indexed(thread_dir: Path, kind: str, link: str):
    """The entry already covering this file, wherever it lives, or None.

    Both indexes, because a retired artifact is still indexed and minting a
    second id for it would leave two entries for one file in two files.
    Returns what a rewrite needs: `(entry, entries, retired)`.
    """
    for retired in (False, True):
        entries = idx.read(thread_dir, kind, retired)
        for entry in entries:
            if entry.link == link:
                return entry, entries, retired
    return None


def _redate(thread_dir: Path, kind: str, entry, entries: list,
            retired: bool, when: date) -> tuple[str, str | None]:
    """Give an indexed file a new date, and with it a new id.

    The only repair for an entry that landed on the epoch, since a filename is
    never renamed and an index line is never hand-edited. The id changes, so
    the reply has to say so: ids are what order_todos and the retire tools
    take, and the caller is holding the old one.

    Removed and re-added rather than edited in place, so it lands where its new
    date puts it instead of where its old one did.
    """
    base = ids_mod.make_id(when, ids_mod.from_filename(PurePosixPath(entry.link).name)[1])
    if base == entry.id:
        return entry.id, None
    was = entry.id
    entries.remove(entry)
    idx.write(thread_dir, kind, entries, retired)
    entry.id = ids_mod.unique_id(base, idx.taken_ids(thread_dir, kind))
    if entry.title == was:
        entry.title = entry.id
    idx.add(thread_dir, kind, entry, retired)
    return entry.id, was


class Indexed(NamedTuple):
    """The entry an index call landed on, and the id it replaced if any."""

    id: str
    was: str | None = None


def _index_one(thread, link: str, description: str = "",
               when: date | None = None) -> tuple[Indexed, Refusal | None]:
    """Derive an entry for one existing file and add it. `(Indexed, error)`.

    Keyed on the file, so a second call amends rather than duplicates. It used
    to mint a fresh id and add a line, which put two entries with two ids on one
    file and reported success for both. Nothing else could edit a description
    either, so a thread that migrated with long ones had no way back.

    No render: the caller does that once, so indexing sixty-six sessions
    rewrites the README once rather than sixty-six times.
    """
    relative = _inside(link)
    if relative is None or len(relative.parts) < 2:
        return Indexed(""), Refusal("OUTSIDE_THREAD")

    kind = relative.parts[0]
    if kind not in _INDEXABLE:
        return Indexed(""), Refusal("NOT_INDEXABLE", kind)

    description = description.strip()
    if len(description) > MAX_DESCRIPTION:
        return Indexed(""), Refusal("DESCRIPTION_TOO_LONG", str(MAX_DESCRIPTION))

    path = thread.dir / relative
    if not path.exists():
        return Indexed(""), Refusal("MISSING")
    if not idx.is_content(path):
        return Indexed(""), Refusal("METADATA")

    default_state, takes_description = _INDEXABLE[kind]

    normalised = f"./{relative}"
    if (found := _already_indexed(thread.dir, kind, normalised)) is not None:
        entry, entries, retired = found
        # An empty description means "not given" rather than "set it to
        # nothing", the same conversion every other optional field makes at this
        # boundary. Without it, re-indexing to correct a link would silently
        # erase the sentence.
        if description and takes_description and entry.description != description:
            was, entry.description = entry.description, description
            if (unreadable := idx.unrepresentable(entry)) is not None:
                entry.description = was
                return Indexed(""), Refusal("UNREPRESENTABLE", unreadable)
            idx.write(thread.dir, kind, entries, retired)
        if when is None:
            return Indexed(entry.id), None
        return Indexed(*_redate(thread.dir, kind, entry, entries, retired, when)), None
    if default_state is _STATE_FROM_FILE:
        state, refusal = _decision_state(path)
        if refusal is not None:
            return Indexed(""), refusal
    else:
        state = default_state

    from_name, rest = ids_mod.from_filename(path.name)
    when = from_name or when
    entry_id = ids_mod.unique_id(
        ids_mod.make_id(when, rest), idx.taken_ids(thread.dir, kind)
    )

    entry = idx.Entry(
        entry_id, state, entry_id, f"./{relative}",
        description if takes_description else "",
    )
    if (unreadable := idx.unrepresentable(entry)) is not None:
        return Indexed(""), Refusal("UNREPRESENTABLE", unreadable)
    idx.add(thread.dir, kind, entry)
    return Indexed(entry_id), None


def index_file(thread, link: str, description: str = "",
               when: str | None = None) -> str:
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
    dated = None
    if when:
        try:
            dated = date.fromisoformat(when)
        except ValueError:
            return json.dumps({"error": "DATE_INVALID", "detail": when})
    indexed, refusal = _index_one(thread, link, description, dated)
    if refusal is not None:
        return json.dumps({"error": refusal.code, "detail": refusal.detail})
    render.render(thread.dir)
    reply: dict = {"id": indexed.id}
    if indexed.was:
        reply["was"] = indexed.was
    if indexed.id.startswith(ids_mod.UNKNOWN):
        reply["undated"] = True
    return json.dumps(reply)


def index_directory(thread, link: str) -> str:
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
        for e in idx.read(thread.dir, kind, retired)
    }
    pending = sorted(
        p for p in directory.iterdir()
        if idx.is_content(p) and p.name not in already
    )

    indexed, unknown = [], []
    refused: dict[str, list[str]] = {}
    for path in pending:
        entry, refusal = _index_one(thread, f"./{kind}/{path.name}")
        if refusal is not None:
            refused.setdefault(refusal.code, []).append(path.name)
            continue
        indexed.append(entry.id)
        if entry.id.startswith(ids_mod.UNKNOWN):
            unknown.append(entry.id)

    if indexed:
        render.render(thread.dir)

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


def _unplaceable(where) -> str:
    """A refusal for a `place` that resolved to nothing.

    The forms are listed only when the form is what was wrong. An anchor that
    is simply not in the list was spelled correctly, and offering the grammar
    there points at the wrong fix.
    """
    reply = {"error": where.error, "detail": where.detail}
    if where.error == "PLACE_UNKNOWN":
        reply["allowed"] = list(todos_mod.PLACES)
    return json.dumps(reply)


def add_todo(thread, title: str, link: str, state: str = "active",
             place: str = "") -> str:
    """Add a todo at a chosen place in the list.

    The caller places it because only the caller knows what the todo is for:
    a piece of the current task goes above it, something that has to follow
    another goes below that one, and anything else goes at the end. One thing
    places itself: `started` means this is what is being worked on, so it goes
    to the top unless a place was named.
    """
    if state not in idx.IN_FORCE["todos"]:
        allowed = list(idx.IN_FORCE["todos"])
        return json.dumps({"error": "STATE_UNKNOWN", "detail": state, "allowed": allowed})
    if not title.strip():
        return json.dumps({"error": "TITLE_REQUIRED"})
    if not link:
        return json.dumps({"error": "LINK_REQUIRED"})
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable

    entries = idx.read(thread.dir, "todos")
    # A place that was asked for wins over the one the state implies.
    at = 0 if state == todos_mod.STARTED else len(entries)
    if place := place.strip():
        where = todos_mod.spot(entries, place)
        if where.at is None:
            return _unplaceable(where)
        at = where.at

    todo_id = _new_id(thread.dir, "todos", title)
    entry = idx.Entry(todo_id, state, title.strip(), link.strip())
    if (unreadable := idx.unrepresentable(entry)) is not None:
        return json.dumps({"error": "UNREPRESENTABLE", "detail": unreadable})
    was = list(entries)
    entries.insert(at, entry)
    idx.write(thread.dir, "todos", entries)
    render.render(thread.dir)
    reply: dict = {"id": todo_id}
    if waiting := todos_mod.just_crowded(was, entries):
        reply["active"] = waiting
    return json.dumps(reply)


def retire_todo(thread, todo_id: str, state: str) -> str:
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    if error := idx.retire(thread.dir, "todos", todo_id, state):
        return json.dumps(error)
    render.render(thread.dir)
    return json.dumps({"id": todo_id})


def set_state(thread, kind: str, entry_id: str, state: str) -> str:
    """Move an entry between in-force states, e.g. parking or starting a todo.

    Two of the todo states carry a position as well as a name, and both are
    applied here rather than left to a second call: `started` means this is
    what is being worked on, and `active` after `parked` means it is wanted
    again but behind whatever became current while it was away.
    """
    if state not in idx.IN_FORCE[kind]:
        return json.dumps({"error": "STATE_UNKNOWN", "detail": state,
                           "allowed": list(idx.IN_FORCE[kind])})
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    entries = idx.read(thread.dir, kind)
    entry = idx.find(entries, entry_id)
    if entry is None:
        return json.dumps({"error": "NO_SUCH_ENTRY", "detail": entry_id})
    before = [idx.Entry(e.id, e.state, e.title, e.link, e.description) for e in entries]
    was, entry.state = entry.state, state
    if kind == "todos":
        if state == todos_mod.STARTED:
            todos_mod.start(entries, entry_id)
        elif state == todos_mod.ACTIVE and was == todos_mod.PARKED:
            todos_mod.to_end(entries, entry_id)
    idx.write(thread.dir, kind, entries)
    render.render(thread.dir)
    reply: dict = {"id": entry_id}
    if kind == "todos" and (waiting := todos_mod.just_crowded(before, entries)):
        reply["active"] = waiting
    return json.dumps(reply)


def order_todos(thread, todo_ids: list[str], place: str = "") -> str:
    """Move the named todos together, in the order given.

    Everything else keeps its relative order, so moving the two items that
    matter does not disturb the rest of the list. The default place is the
    top, which is what reordering is usually for.
    """
    if not todo_ids:
        return json.dumps({"error": "IDS_REQUIRED"})
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    entries = idx.read(thread.dir, "todos")
    known = {e.id for e in entries}
    if missing := [i for i in todo_ids if i not in known]:
        return json.dumps({"error": "NO_SUCH_ENTRY", "detail": ", ".join(missing)})
    # Refused rather than de-duplicated: collapsing a repeat would produce an
    # order nobody asked for, and say nothing about having done so.
    if repeated := [i for i in set(todo_ids) if todo_ids.count(i) > 1]:
        return json.dumps({"error": "DUPLICATE_ID", "detail": ", ".join(sorted(repeated))})

    # Resolved against the list the movers have been taken out of, which is
    # also what makes an anchor that is itself moving impossible to resolve.
    staying = todos_mod.staying(entries, todo_ids)
    where = todos_mod.spot(staying, place) if place.strip() else todos_mod.Spot(0)
    if where.at is None:
        if where.error == "NO_SUCH_ENTRY" and where.detail in todo_ids:
            return json.dumps({"error": "ANCHOR_IS_MOVING", "detail": where.detail})
        return _unplaceable(where)
    idx.write(thread.dir, "todos",
              todos_mod.reordered(entries, todo_ids, where.at))
    render.render(thread.dir)
    return json.dumps({"ordered": len(todo_ids)})


def log_decision(thread, title: str, summary: str, body: str,
                 status: str = "proposed",
                 supersedes: list[str] | None = None) -> str:
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
    indexed = index_file(thread, f"./decisions/{decision_id}.md")
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
    entries = idx.read(thread.dir, "decisions")
    entry = idx.find(entries, decision_id)
    if error := idx.retire(thread.dir, "decisions", decision_id, state):
        return json.dumps(error)
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
    if error := idx.retire(thread.dir, "artifacts", artifact_id, state):
        return json.dumps(error)
    render.render(thread.dir)
    return json.dumps({"id": artifact_id})


def save_session(thread, slug: str, summary: str, keywords: str, body: str,
                 status: str | None = None) -> str:
    """Everything a save does that is not synthesis.

    The incremental tools have already written todos, decisions and artifacts as
    they happened, so a save is down to the session log and the Status
    paragraph. A session that dies before this still leaves its stub and a
    record of what it touched.
    """
    from ai_workspace.threads.v2 import readme as readme_mod

    if not body.strip():
        return json.dumps({"error": "BODY_EMPTY"})
    if (unwritable := render.blocked(thread.dir)) is not None:
        return unwritable
    session_id, _ = session.save(thread.dir, slug, summary, keywords, body)
    if status:
        readme_mod.set_status(thread.dir, status)
    readme_mod.touch_dates(thread.dir)
    render.render(thread.dir)
    return json.dumps({"id": session_id, "status_written": bool(status)})
