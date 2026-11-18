"""Per-type index files: the record of what a thread contains.

An index sits beside its directory rather than inside it, so a directory scan
never picks up its own index and `decisions/*.md` keeps meaning exactly
"decisions".

Each index is a JSON document, `{"entries": [...]}`, written only here and
never by hand unless it no longer parses. An entry has named fields: `id`,
`state`, `title`, `link`, `description`, `star`, `children` and `parent`. A
field is written only when it is set, except that `children` is written
whenever it is not None, so an empty list stays an empty list. Sessions carry
no `state`.

Keys this module does not know are kept, on entries, on their children and at
the top of the document, and are written back unchanged. Every entry and every
child sits on its own line, so a diff and a grep both see one entry at a time.

A file that does not parse raises `UnreadableIndex`. It is never read as empty
and never overwritten, because an empty index is valid and the next write
would lose the record.

The one-line `- id:state [title](link) -- description` form survives only as
`Entry.render`, a display rendering that is never read back.

A decision's or a session's `summary:` never appears here. It is already in the
file, so a copy would drift the moment anyone edits it, which the log-decision
command explicitly invites.

That argument does not reach artifacts. They have no template, no required
frontmatter, and can be a PDF or a directory, so the entry is the only home a
description has and there is no second copy to drift from. Artifacts are the
only kind that carries one.
"""

import contextlib
import json
import os
import tempfile
from pathlib import Path

FIX = ("Repair this file by hand so it parses, then retry. Do not delete or "
       "recreate it: an empty index reads as valid and loses the record.")

TYPES = ("sessions", "decisions", "artifacts", "todos")
RETIRED_TYPES = ("decisions", "artifacts", "todos")

# Kinds whose entry order is a priority the user set rather than a chronology.
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


class UnreadableIndex(Exception):
    """An index file that does not parse or is not the shape described above."""

    def __init__(self, file: str, detail: str) -> None:
        super().__init__(f"{file}: {detail}")
        self.file, self.detail = file, detail

    def payload(self) -> dict:
        return {"error": "UNREADABLE_INDEX", "file": self.file,
                "detail": self.detail, "fix": FIX}


_STRINGS = ("state", "description", "star", "parent")
_KNOWN = frozenset(("id", "title", "link", "children", *_STRINGS))


def _one_line(value: str) -> str:
    return " ".join(value.splitlines())


class Entry:
    """One indexed thing. Fields are optional per kind rather than per entry:
    sessions never carry a state, only artifacts carry a description or a star,
    only a todo carries children or a parent."""

    __slots__ = ("children", "description", "extra", "id", "link", "parent",
                 "star", "state", "title")

    def __init__(self, id: str, state: str | None, title: str, link: str,
                 description: str = "", *, star: str | None = None,
                 children: "list[Entry] | None" = None,
                 parent: str | None = None,
                 extra: dict | None = None) -> None:
        self.id, self.state, self.title, self.link = id, state, title, link
        self.description, self.star = description, star
        self.children, self.parent = children, parent
        self.extra = {} if extra is None else extra

    def render(self, state: str | None = None) -> str:
        """The display line. `state` shows in place of the stored one."""
        shown = state or self.state
        mark = f":{shown}" if shown else ""
        tail = f" -- {_one_line(self.description)}" if self.description else ""
        return (f"- {_one_line(self.id)}{mark} "
                f"[{_one_line(self.title)}]({_one_line(self.link)}){tail}")

    def _known(self) -> dict:
        """The fields that are set, without `children` or unknown keys."""
        out: dict = {"id": self.id}
        for name in ("state", "title", "link", "description", "star", "parent"):
            value = getattr(self, name)
            if value is not None and value != "":
                out[name] = value
        return out

    def to_json(self) -> dict:
        out = self._known()
        if self.children is not None:
            out["children"] = [c.to_json() for c in self.children]
        out.update(self.extra)
        return out

    @classmethod
    def from_json(cls, obj: object) -> "Entry":
        if not isinstance(obj, dict):
            raise ValueError("not an object")
        for name in ("id", "title", "link"):
            if not isinstance(obj.get(name), str):
                raise ValueError(f"{name} is missing or not a string")
        for name in _STRINGS:
            if name in obj and not isinstance(obj[name], str):
                raise ValueError(f"{name} is not a string")
        children = None
        if "children" in obj:
            raw = obj["children"]
            if not isinstance(raw, list):
                raise ValueError("children is not a list")
            children = []
            for n, child in enumerate(raw, 1):
                try:
                    children.append(cls.from_json(child))
                except ValueError as err:
                    raise ValueError(f"child {n}: {err}") from None
        return cls(obj["id"], obj.get("state"), obj["title"], obj["link"],
                   obj.get("description", ""), star=obj.get("star"),
                   children=children, parent=obj.get("parent"),
                   extra={k: v for k, v in obj.items() if k not in _KNOWN})

    def __repr__(self) -> str:
        return f"Entry({self.id!r}, {self.state!r}, {self.title!r})"


def external(link: str) -> bool:
    """Whether this link names something outside the workspace entirely.

    Whether a URL is the right link for a todo is a judgement call, and the
    skill and `add_todo`'s docstring state that rule. This function answers
    only whether a link is external at all. A reader that resolves links as
    `thread_dir / link` needs that, so it can let an external link past instead
    of calling it missing. One definition, because a writer that accepts a link
    and an auditor that calls the same link dangling is worse than either rule
    on its own.
    """
    return link.lower().startswith(("http://", "https://"))


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
    return thread_dir / f"{kind}-{suffix}.json"


def _load(path: Path) -> tuple[dict, list[Entry]]:
    """The whole document and its entries. A file that is not the shape this
    module writes raises `UnreadableIndex`, naming the fault."""
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise UnreadableIndex(path.name, str(err)) from None
    except UnicodeDecodeError as err:
        raise UnreadableIndex(path.name, f"not UTF-8 text: {err}") from None
    if not isinstance(doc, dict):
        raise UnreadableIndex(path.name, "the document is not an object")
    raw = doc.get("entries")
    if not isinstance(raw, list):
        raise UnreadableIndex(path.name, 'the document has no "entries" list')
    entries = []
    for n, item in enumerate(raw, 1):
        try:
            entries.append(Entry.from_json(item))
        except ValueError as err:
            raise UnreadableIndex(path.name, f"entry {n}: {err}") from None
    return doc, entries


def read(thread_dir: Path, kind: str, retired: bool = False) -> list[Entry]:
    """The entries, in file order. A missing index is an empty index.

    Nothing pre-creates index files, so absence is normal rather than an error:
    they appear the first time something is written to them. That is only safe
    because the shape marker is its own file: were absence of an index the
    sentinel, tolerating a missing one would be indistinguishable from schema 1.

    A file that exists but does not parse raises `UnreadableIndex`, and that
    includes an empty or whitespace-only one.
    """
    path = index_path(thread_dir, kind, retired)
    if not path.exists():
        return []
    return _load(path)[1]


def _dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _lines(entry: Entry, depth: int) -> list[str]:
    """The entry as lines, the last without a trailing comma. A goal spreads
    over several so that each child has a line of its own."""
    pad = "  " * depth
    if not entry.children:
        return [pad + _dumps(entry.to_json())]
    out = [f'{pad}{_dumps(entry._known())[:-1]}, "children": [']
    kids = [_lines(child, depth + 1) for child in entry.children]
    for kid in kids[:-1]:
        kid[-1] += ","
    for kid in kids:
        out.extend(kid)
    extra = "".join(f", {_dumps(k)}: {_dumps(v)}" for k, v in entry.extra.items())
    out.append(f"{pad}]{extra}}}")
    return out


def write(thread_dir: Path, kind: str, entries: list[Entry],
          retired: bool = False) -> Path:
    """Write the whole list, atomically.

    A file already there is parsed first, so one that does not parse is never
    overwritten, and its other top-level keys are written back unchanged. The
    new content goes to a temp file beside it and `os.replace` swaps it in, so
    a reader sees the old file or the new one and a failure leaves the old.
    """
    path = index_path(thread_dir, kind, retired)
    others: dict = {}
    mode = 0o644
    if path.exists():
        doc, _ = _load(path)
        others = {k: v for k, v in doc.items() if k != "entries"}
        mode = path.stat().st_mode & 0o777
    rows: list[str] = []
    for i, e in enumerate(entries):
        lines = _lines(e, 2)
        if i < len(entries) - 1:
            lines[-1] += ","
        rows.extend(lines)
    tail = "".join(f", {_dumps(k)}: {_dumps(v)}" for k, v in others.items())
    if rows:
        text = "\n".join(['{"entries": [', *rows, "  ]" + tail + "}"]) + "\n"
    else:
        text = '{"entries": []' + tail + "}\n"
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.",
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise
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
