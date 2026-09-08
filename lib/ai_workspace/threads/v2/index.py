"""Per-type index files: the record of what a thread contains.

An index sits beside its directory rather than inside it, so a directory scan
never picks up its own index and `decisions/*.md` keeps meaning exactly
"decisions".

Line format, written only here and never by hand:

    - 20260723-prep-ladder:locked [Interview prep ladder](./decisions/20260723-prep-ladder.md)
    - 20260316-notes:current [20260316-notes](./artifacts/20260316-notes.md) -- what it contains

`id:state`, a linked title, then an optional description. `^- <id>:` is an exact
match because the colon terminates the id. Sessions carry a bare id with no
state.

A decision's or a session's `summary:` never appears here. It is already in the
file, so a copy would drift the moment anyone edits it, which the log-decision
command explicitly invites.

That argument does not reach artifacts. They have no template, no required
frontmatter, and can be a PDF or a directory, so the line is the only home a
description has and there is no second copy to drift from. Artifacts are the
only kind that carries one.
"""

import re
from pathlib import Path

from ai_workspace.text import split_frontmatter

TYPES = ("sessions", "decisions", "artifacts", "todos")
RETIRED_TYPES = ("decisions", "artifacts", "todos")

IN_FORCE = {
    "decisions": ("proposed", "partially-locked", "locked"),
    "todos": ("active", "parked"),
    "artifacts": ("current",),
    "sessions": (),
}
RETIRED = {
    "decisions": ("superseded", "withdrawn"),
    "todos": ("done", "dropped"),
    "artifacts": ("superseded", "stale"),
    "sessions": (),
}

_LINE_RE = re.compile(
    r"^- (?P<id>[^\s:]+)(?::(?P<state>[^\s]+))? "
    r"\[(?P<title>[^\]]*)\]\((?P<link>[^)]*)\)"
    r"(?: -- (?P<description>.*?))?\s*$"
)


class Entry:
    """One indexed thing. Both tails are optional, and per kind rather than per
    entry: sessions never carry a state, only artifacts carry a description."""

    __slots__ = ("id", "state", "title", "link", "description")

    def __init__(self, id: str, state: str | None, title: str, link: str,
                 description: str = ""):
        self.id, self.state, self.title, self.link = id, state, title, link
        self.description = description

    def render(self) -> str:
        state = f":{self.state}" if self.state else ""
        tail = f" -- {self.description}" if self.description else ""
        return f"- {self.id}{state} [{self.title}]({self.link}){tail}"

    def __repr__(self) -> str:
        return f"Entry({self.id!r}, {self.state!r}, {self.title!r})"


def index_path(thread_dir: Path, kind: str, retired: bool = False) -> Path:
    suffix = "retired" if retired else "index"
    return thread_dir / f"{kind}-{suffix}.md"


def read(thread_dir: Path, kind: str, retired: bool = False) -> tuple[list[Entry], dict]:
    """Return (entries, frontmatter). A missing index is an empty index.

    Nothing pre-creates index files, so absence is normal rather than an error:
    they appear the first time something is written to them. That is only safe
    because the shape marker is its own file — were absence of an index the
    sentinel, tolerating a missing one would be indistinguishable from schema 1.
    """
    path = index_path(thread_dir, kind, retired)
    if not path.exists():
        return [], {}
    fields, body = split_frontmatter(path.read_text(), path)
    windows = fields.get("windows")
    fm: dict = {"windows": windows} if isinstance(windows, dict) else {}
    entries = []
    for line in body.splitlines():
        hit = _LINE_RE.match(line)
        if hit:
            entries.append(Entry(hit["id"], hit["state"], hit["title"], hit["link"],
                                 hit["description"] or ""))
    return entries, fm


def _render(entries: list[Entry], fm: dict) -> str:
    out = []
    windows = fm.get("windows") or {}
    if windows:
        out.append("---")
        out.append("windows:")
        for name, ids in windows.items():
            out.append(f"  {name}: [{', '.join(ids)}]")
        out.append("---")
        out.append("")
    out.extend(e.render() for e in entries)
    return "\n".join(out) + ("\n" if out else "")


def write(thread_dir: Path, kind: str, entries: list[Entry], fm: dict,
          retired: bool = False) -> Path:
    path = index_path(thread_dir, kind, retired)
    path.write_text(_render(entries, fm))
    return path


def add(thread_dir: Path, kind: str, entry: Entry, retired: bool = False) -> Path:
    """Insert an entry in id order.

    Ids are YYYYMMDD-slug, so id order is chronological and a string comparison
    places the entry without parsing a date. Usually the new entry is the newest
    and this is an append, but not always: a session recovered from a transcript
    after later ones were already saved belongs where its date puts it.

    Scanning back from the end leaves an index that is already out of order in
    the order it was, rather than silently reordering lines nobody asked about.
    """
    entries, fm = read(thread_dir, kind, retired)
    at = len(entries)
    while at and entries[at - 1].id > entry.id:
        at -= 1
    entries.insert(at, entry)
    return write(thread_dir, kind, entries, fm, retired)


def find(entries: list[Entry], entry_id: str) -> Entry | None:
    return next((e for e in entries if e.id == entry_id), None)


def taken_ids(thread_dir: Path, kind: str) -> set[str]:
    live, _ = read(thread_dir, kind)
    gone, _ = read(thread_dir, kind, retired=True)
    return {e.id for e in live} | {e.id for e in gone}


def retire(thread_dir: Path, kind: str, entry_id: str, state: str) -> str | None:
    """Move one line from the index to the retired index. Returns an error or None."""
    if kind not in RETIRED_TYPES:
        return f"Error: {kind} entries do not retire."
    if state not in RETIRED[kind]:
        allowed = ", ".join(RETIRED[kind])
        return f"Error: '{state}' is not a retired state for {kind}. Use one of: {allowed}."
    entries, fm = read(thread_dir, kind)
    entry = find(entries, entry_id)
    if entry is None:
        return f"Error: No {kind} entry with id '{entry_id}'."
    entries.remove(entry)
    entry.state = state
    write(thread_dir, kind, entries, fm)
    add(thread_dir, kind, entry, retired=True)
    return None


def set_window(thread_dir: Path, kind: str, section: str, ids: list[str]) -> str | None:
    entries, fm = read(thread_dir, kind)
    known = {e.id for e in entries}
    missing = [i for i in ids if i not in known]
    if missing:
        return f"Error: no {kind} entry for: {', '.join(missing)}."
    windows = dict(fm.get("windows") or {})
    windows[section] = ids
    write(thread_dir, kind, entries, {"windows": windows})
    return None
