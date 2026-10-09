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

TYPES = ("sessions", "decisions", "artifacts", "todos")
RETIRED_TYPES = ("decisions", "artifacts", "todos")

# Kinds whose line order is a priority the user set rather than a chronology.
# Nothing may re-sort one, and the migration audit must not expect dates in it.
# `add` is not involved: the tool that knows the order writes the whole list,
# and the only index `add` touches for an ORDERED kind is the retired one,
# which is a record of what happened and so is dated like any other.
ORDERED = ("todos",)

IN_FORCE = {
    "decisions": ("proposed", "partially-locked", "locked"),
    "todos": ("active", "started", "parked"),
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

    __slots__ = ("description", "id", "link", "state", "title")

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


def _parts(entry: Entry) -> dict[str, str]:
    """The entry's fields by the name `_LINE_RE` gives each group."""
    return {"id": entry.id, "state": entry.state or "", "title": entry.title,
            "link": entry.link, "description": entry.description}


def _with(entry: Entry, field: str, value: str) -> Entry:
    parts = _parts(entry)
    parts[field] = value
    return Entry(**parts)


def _round_trips(entry: Entry) -> bool:
    """Whether reading this entry's own line back gives the entry again."""
    hit = _LINE_RE.match(entry.render())
    if hit is None:
        return False
    return all((hit[field] or "") == value for field, value in _parts(entry).items())


def unrepresentable(entry: Entry) -> str | None:
    r"""Which of this entry's fields would not survive a line, or None.

    A field that ends its own delimiter writes a line `_LINE_RE` reads back
    differently or not at all. A title carrying "]" and a link carrying ")"
    lose the entry outright; a description carrying a line break truncates and
    orphans the rest. `Merge_(SQL)` is an ordinary Wikipedia URL, so none of
    this needs trying.

    Rendered and read back rather than screened against a list of characters,
    so the check cannot disagree with the pattern that does the reading: it is
    that pattern. A field added to the line later is covered without anyone
    remembering to extend a table.

    The line-break test is separate because `read` splits the file into lines
    before matching, so a break inside a field makes a line the pattern never
    sees, and `[^\]]` matches a newline in any case.

    Refused rather than escaped, for the reason an over-long description is:
    the caller wrote the text and is still holding it, so it is the only party
    that can fix it, and an escape scheme is a second parser to keep in
    agreement with the first.
    """
    for field, value in _parts(entry).items():
        if value and ("\n" in value or "\r" in value):
            return f"{field} contains a line break"
    if _round_trips(entry):
        return None
    # Name the field at fault by putting a value known to be safe in its place.
    # The one whose replacement makes the line read back is the one that broke
    # it, and asking the pattern is the only way to find out that cannot
    # disagree with the pattern.
    for field, value in _parts(entry).items():
        if value and _round_trips(_with(entry, field, "x")):
            return f"{field} cannot be read back from a line"
    return "the line it makes cannot be read back"


def is_content(path: Path) -> bool:
    """Whether a directory entry is thread content rather than filesystem noise.

    A leading dot means metadata. `.DS_Store`, and the `._name` AppleDouble
    files macOS writes beside every file when copying to a filesystem with no
    resource forks, which is what a NAS or a memory stick is. A real thread had
    one of those per file: fifty in two directories.

    They cannot merely be skipped as an afterthought, because `._20260125-x.md`
    sorts before `20260125-x.md` and would otherwise take that session's id and
    leave the real file holding `-2`.
    """
    return not path.name.startswith(".")


def index_path(thread_dir: Path, kind: str, retired: bool = False) -> Path:
    suffix = "retired" if retired else "index"
    return thread_dir / f"{kind}-{suffix}.md"


# The ids a `windows:` frontmatter block names. Indexes written before a todo
# list carried its own order open with one, naming the todos Next steps showed.
# Matched with a pattern rather than read with a YAML parser because one real
# block is indented with a tab, which no parser accepts, and because the block
# is the only thing in it anything still wants.
_LEGACY_WINDOW = re.compile(r"(?m)^\s*next_steps:\s*\[([^\]]*)\]")


def _window_first(text: str, entries: list[Entry]) -> list[Entry]:
    """Entries with the todos that block named first, in the order it gave.

    That order is a priority the user set, so it becomes line order, which is
    where this schema keeps priority. The next write makes it permanent and
    the block goes. An id the block names that is no longer in the index was
    retired in between, and is skipped.
    """
    found = _LEGACY_WINDOW.search(text)
    if not found:
        return entries
    named = [i.strip() for i in found.group(1).split(",") if i.strip()]
    by_id = {e.id: e for e in entries}
    first = [by_id[i] for i in named if i in by_id]
    return first + [e for e in entries if e.id not in set(named)]


def read(thread_dir: Path, kind: str, retired: bool = False) -> list[Entry]:
    """The entries, in file order. A missing index is an empty index.

    Nothing pre-creates index files, so absence is normal rather than an error:
    they appear the first time something is written to them. That is only safe
    because the shape marker is its own file — were absence of an index the
    sentinel, tolerating a missing one would be indistinguishable from schema 1.

    Lines are matched rather than parsed around, so anything that is not an
    entry is skipped. The one thing read out of what is left is a `windows:`
    block, whose order this schema keeps as line order instead.
    """
    path = index_path(thread_dir, kind, retired)
    if not path.exists():
        return []
    text = path.read_text()
    entries = []
    for line in text.splitlines():
        hit = _LINE_RE.match(line)
        if hit:
            entries.append(Entry(hit["id"], hit["state"], hit["title"], hit["link"],
                                 hit["description"] or ""))
    # Only where one was ever written, and only where order means anything: a
    # retired index is a chronology, so a block in one would be reordering a
    # record of what happened.
    if kind in ORDERED and not retired:
        return _window_first(text, entries)
    return entries


def write(thread_dir: Path, kind: str, entries: list[Entry],
          retired: bool = False) -> Path:
    path = index_path(thread_dir, kind, retired)
    lines = [e.render() for e in entries]
    path.write_text("\n".join(lines) + ("\n" if lines else ""))
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
    entries = read(thread_dir, kind, retired)
    at = len(entries)
    while at and entries[at - 1].id > entry.id:
        at -= 1
    entries.insert(at, entry)
    return write(thread_dir, kind, entries, retired)


def find(entries: list[Entry], entry_id: str) -> Entry | None:
    return next((e for e in entries if e.id == entry_id), None)


def taken_ids(thread_dir: Path, kind: str) -> set[str]:
    live = read(thread_dir, kind)
    gone = read(thread_dir, kind, retired=True)
    return {e.id for e in live} | {e.id for e in gone}


def retire(thread_dir: Path, kind: str, entry_id: str, state: str) -> dict | None:
    """Move one line from the index to the retired index.

    A refusal payload, or None. A payload rather than a sentence, because every
    other write on this schema answers a machine with a code, and a caller
    parsing that contract breaks on a bare string. The dict is JSON-ready;
    serialising it is the tool layer's job.
    """
    if kind not in RETIRED_TYPES:
        return {"error": "NOT_RETIRABLE", "detail": kind}
    if state not in RETIRED[kind]:
        return {"error": "STATE_UNKNOWN", "detail": state,
                "allowed": list(RETIRED[kind])}
    entries = read(thread_dir, kind)
    entry = find(entries, entry_id)
    if entry is None:
        return {"error": "NO_SUCH_ENTRY", "detail": entry_id}
    entries.remove(entry)
    entry.state = state
    write(thread_dir, kind, entries)
    add(thread_dir, kind, entry, retired=True)
    return None
