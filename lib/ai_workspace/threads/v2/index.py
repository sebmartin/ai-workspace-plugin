"""Per-type index files: the record of what a thread contains.

An index sits beside its directory rather than inside it, so a directory scan
never picks up its own index and `decisions/*.md` keeps meaning exactly
"decisions".

Line format, written only here and never by hand:

    - 20260723-prep-ladder:locked [Interview prep ladder](./decisions/20260723-prep-ladder.md)

`id:state` then a linked title. `^- <id>:` is an exact match because the colon
terminates the id. Sessions carry a bare id with no state.

There is deliberately no description on the line. Carrying a decision's
`summary:` here would be a second copy of something the file already states, and
it would drift the moment anyone edits the file, which the log-decision command
explicitly invites. The index says what exists and what state it is in; the file
says what it means.
"""

import re
from pathlib import Path

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

_LINE_RE = re.compile(r"^- (?P<id>[^\s:]+)(?::(?P<state>[^\s]+))? \[(?P<title>[^\]]*)\]\((?P<link>[^)]*)\)\s*$")
_FM_RE = re.compile(r"\A---\s*\n(?P<body>.*?)\n---\s*\n", re.DOTALL)


class Entry:
    __slots__ = ("id", "state", "title", "link")

    def __init__(self, id: str, state: str | None, title: str, link: str):
        self.id, self.state, self.title, self.link = id, state, title, link

    def render(self) -> str:
        state = f":{self.state}" if self.state else ""
        return f"- {self.id}{state} [{self.title}]({self.link})"

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
    text = path.read_text()
    fm: dict = {}
    m = _FM_RE.match(text)
    if m:
        fm = _parse_windows(m.group("body"))
        text = text[m.end():]
    entries = []
    for line in text.splitlines():
        hit = _LINE_RE.match(line)
        if hit:
            entries.append(Entry(hit["id"], hit["state"], hit["title"], hit["link"]))
    return entries, fm


def _parse_windows(body: str) -> dict:
    """Read the `windows:` block without a YAML dependency.

    The codebase has no YAML parser and frontmatter is read with regex
    elsewhere; this keeps that consistent rather than adding a dependency for
    one nested mapping.
    """
    windows: dict[str, list[str]] = {}
    in_windows = False
    for line in body.splitlines():
        if line.strip() == "windows:":
            in_windows = True
            continue
        if in_windows:
            if line.startswith("  ") and ":" in line:
                name, _, value = line.strip().partition(":")
                value = value.strip()
                if value.startswith("[") and value.endswith("]"):
                    ids = [i.strip() for i in value[1:-1].split(",") if i.strip()]
                    windows[name] = ids
                continue
            if line.strip():
                in_windows = False
    return {"windows": windows} if windows else {}


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


def append(thread_dir: Path, kind: str, entry: Entry, retired: bool = False) -> Path:
    """Add an entry to the end.

    Append rather than sorted insert: in normal use every new entry is the
    newest one, so appending is correct and never rewrites an earlier line.
    Migration is the only bulk writer and iterates in date order itself, which
    is an instruction in its guidance rather than a cost paid on every write.
    """
    entries, fm = read(thread_dir, kind, retired)
    entries.append(entry)
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
    append(thread_dir, kind, entry, retired=True)
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
